import math
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
       
        self.bot_pos = None
        self.bot_rot = None


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
        current_team = my_car.team
        
        
        # Blue and Orange team goal targets
        orange_goal_target = Vec3(0, 5000, 321.3875)
        blue_goal_target = Vec3(0, -5000, 321.3875)

        # Test if team is orange
        if current_team == 1:
            target_location = orange_goal_target
        else:
            target_location = blue_goal_target
  

        if self.car_location.dist(target_location) > 5000:
            self.controls.steer = steer_toward_target(my_car, target_location)
            self.controls.throttle = 1.0
        else:
            self.controls.throttle = 0

        if ball_location.dist(target_location) < 5000:
            target_location = ball_location
            self.controls.steer = steer_toward_target(my_car, target_location)
            self.controls.throttle = 1.0
        elif self.car_location.dist(target_location) > 3200:
            target_location = orange_goal_target
            self.controls.steer = steer_toward_target(my_car, target_location)
            self.controls.throttle = 1.0
        
        self.aim(target_location.x, target_location.y)

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
            

 