import math
import time
from turtle import distance
from rlbot.agents.base_agent import BaseAgent, SimpleControllerState
from rlbot.messages.flat.QuickChatSelection import QuickChatSelection
from rlbot.utils.structures.game_data_struct import GameTickPacket

from util.ball_prediction_analysis import GOAL_SEARCH_INCREMENT, find_slice_at_time
from util.boost_pad_tracker import BoostPadTracker
from util.drive import steer_toward_target
from util.sequence import Sequence, ControlStep
from util.vec import Vec3


class MyBot(BaseAgent):

    def __init__(self, name, team, index):
        super().__init__(name, team, index)
        self.active_sequence: Sequence = None
        self.boost_pad_tracker = BoostPadTracker()
        self.controls = SimpleControllerState()

        #Dodge variables
        self.should_dodge = False
        self.on_second_jump = False
        self.next_dodge_time = 0
        
        self.DODGE_TIME = 0.2
        self.DISTANCE_TO_DODGE = 500

    def initialize_agent(self):
        # Set up information about the boost pads now that the game is active and the info is available
        self.boost_pad_tracker.initialize_boosts(self.get_field_info())
        

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
            controls = self.active_sequence.tick(packet)
            if controls is not None:
                return controls

        # Gather some information about our car, ball and goal
        my_car = packet.game_cars[self.index]
        self.car_location = Vec3(my_car.physics.location)
        self.car_yaw = my_car.physics.rotation.yaw
        ball_location = Vec3(packet.game_ball.physics.location)
    
        
        
        
        # Blue and Orange team goal targets
        orange_goal_target = Vec3(0, 5000, 321.3875)
        blue_goal_target = Vec3(0, -5000, 321.3875)

        # Test if team is orange
        if self.team == 1:
            goal_location = orange_goal_target
        else:
            goal_location = blue_goal_target

        if self.car_location.dist(goal_location) > 5000:
            self.aim(goal_location.x, goal_location.y)
            self.controls.throttle = 1.0
        else:
            self.controls.throttle = 0

        if ball_location.dist(goal_location) < 5000:
            self.aim(ball_location.x, ball_location.y)
            self.controls.throttle = 1.0
            if (self.team == 1 and self.car_location.y > ball_location.y) or (self.team == 0 and self.car_location.y < ball_location.y):
                self.aim(ball_location.x, ball_location.y)
                if distance(self.car_location.x, self.car_location.y, ball_location.x, ball_location.y) < self.DISTANCE_TO_DODGE:
                    self.should_dodge = True
                else:
                    self.aim(goal_location.x, goal_location.y)

        elif self.car_location.dist(goal_location) > 3200:
            self.aim(goal_location.x, goal_location.y)
            self.controls.throttle = 1.0

        self.controls.jump = 0

        self.check_for_dodge()

        return self.controls

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
        
    def check_for_dodge(self):
        if self.should_dodge and time.time() > self.next_dodge_time:
            self.controls.jump = True
            self.controls.pitch = -1

        if self.on_second_jump:
            self.on_second_jump = False
            self.should_dodge = time.time() + self.DODGE_TIME

    def distance(x1, y1, x2, y2):
        return math.sqrt((x2 -x1)**2 + (y2 - y1)**2)
   

 