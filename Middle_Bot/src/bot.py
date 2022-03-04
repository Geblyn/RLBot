import math
import time
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket
from rlbot.utils.structures.quick_chats import QuickChats

from util.ball_prediction_analysis import find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3

# Code needs to be tested, gets variable score (quick chat)
def get_game_score(packet : GameTickPacket):
        score = [0, 0]

        for car in packet.game_cars:
            score[car.team] += car.score_info.goals
        
        return score
# end of code (quick chat)

class MyBot(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.active_sequence: Sequence = None
        self.boost_pad_tracker = BoostPadTracker()
        self.DISTANCE_TO_BOOST = 1500
        self.DODGE_TIME = .2

        self.should_flip = False
        self.on_second_jump = False
        self.next_dodge_time = 5
        

    def initialize_agent(self):
        # Set up information about the boost pads now that the game is active and the info is available
        self.boost_pad_tracker.initialize_boosts(self.get_field_info())
        self.previous_frame_team_score = 0

    def aim(self, target_x, target_y):
        angle_between_bot_and_target = math.atan2(target_y - self.car_location.y, target_x - self.car_location.x)

        angle_front_to_target = angle_between_bot_and_target - self.car_yaw

        if angle_front_to_target < -math.pi:
            angle_front_to_target += 2 * math.pi
        if angle_front_to_target > math.pi:
            angle_front_to_target -= 2 * math.pi

        if angle_front_to_target < math.radians(-10):
            self.controls.steer = -1
        elif angle_front_to_target > math.radians(10):
            self.controls.steer = 1
        else:
            self.controls.steer = 0

    def check_for_filp(self):
        if self.should_flip and time.time() > self.next_dodge_time:
            self.controls.jump = True
            self.controls.pitch = -1

            if self.on_second_jump:
                self.on_second_jump = False
                self.should_flip = False
            else:
                self.on_second_jump = True
                self.next_dodge_time = time.time() + self.DODGE_TIME

    def Distance(self, x1, y1, x2, y2):
        return math.sqrt((x2 -x1)**2 + (y2 - y1)**2)


    def get_output(self, packet: GameTickPacket) -> SimpleControllerState:
        """
        This function will be called by the framework many times per second. This is where you can
        see the motion of the ball, etc. and return controls to drive your car.
        """
        # Keep our boost pad info updated with which pads are currently active
        self.boost_pad_tracker.update_boost_status(packet)

        # This is good to keep at the beginning of get_output. It will allow you to continue
        # any sequences that you may have started during a previous call to get_output.
        if self.active_sequence is not None and not self.active_sequence.done:
            self.controls = self.active_sequence.tick(packet)
            if self.controls is not None:
                return self.controls

        # Gather some information about our car and the ball
        my_car = packet.game_cars[self.index]
        self.car_location = Vec3(my_car.physics.location)
        self.car_yaw = my_car.physics.rotation.yaw
        car_velocity = Vec3(my_car.physics.velocity)
        self.ball_location = Vec3(packet.game_ball.physics.location)

        if self.team == 1:
            goal_location = Vec3(0, 5000, 321.3875)
            enemy_goal = Vec3(0, -5000, 321.3875)
        else:
            goal_location = Vec3(0, -5000, 321.3875)
            enemy_goal = Vec3(0, 5000, 321.3875)

        self.controls = SimpleControllerState()
        
        if self.Distance(self.car_location.x, self.car_location.y, 0, 0) > 2500:
            self.aim(0, 0)
            self.controls.throttle = 1.0
        else:
            self.controls.throttle = 0

        if self.Distance(self.ball_location.x, self.ball_location.y, 0, 0) < 2500:
            self.aim(self.ball_location.x, self.ball_location.y)
            self.controls.throttle = 1.0

        
        if (self.team == 0 and self.car_location.y < self.ball_location.y) or (self.team == 1 and self.car_location.y > self.ball_location.y):
            if self.ball_location.dist(goal_location) > 5000:
                if self.car_location.dist(self.ball_location) < 350:
                    self.aim(self.ball_location.x, self.ball_location.y)
                    self.controls.throttle = 1.0
                    self.should_flip = True
        else:
                self.aim(0,0)

        if self.ball_location.dist(enemy_goal) < 2000 and self.ball_location.x < 893 and self.ball_location.dist(enemy_goal) < 2000 and self.ball_location.x > -893:
            self.aim(self.ball_location.x, self.ball_location.y)
            self.controls.throttle = 1.0
            self.controls.boost = True
            self.should_flip = False

        current_score = get_game_score(packet)
        self. previous_frame_team_score = current_score[self.team]
        if self.previous_frame_team_score < current_score[self.team]:
            self.send_quick_chat(QuickChats.CHAT_EVERYONE, QuickChats.Custom_Toxic_404NoSkill)
        

        self.controls.jump = 0

        self.check_for_filp()

        return self.controls
    
    def begin_front_flip(self, packet):
        # Send some quickchat just for fun
        self.send_quick_chat(team_only=False, quick_chat=QuickChatSelection.Information_IGotIt)

        # Do a front flip. We will be committed to this for a few seconds and the bot will ignore other
        # logic during that time because we are setting the active_sequence.
        self.active_sequence = Sequence([
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=True)),
            ControlStep(duration=0.05, controls=SimpleControllerState(jump=False)),
            ControlStep(duration=0.2, controls=SimpleControllerState(jump=True, pitch=-1)),
            ControlStep(duration=0.8, controls=SimpleControllerState()),
        ])

    

        # Return the controls associated with the beginning of the sequence so we can start right away.
        return self.active_sequence.tick(packet)



