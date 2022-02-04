from multiprocessing.connection import wait
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
        car_location = Vec3(my_car.physics.location)
        car_velocity = Vec3(my_car.physics.velocity)
        ball_location = Vec3(packet.game_ball.physics.location)
        current_team = my_car.team
        
        # Blue and Orange team goal targets
        orange_goal_target = Vec3(0, 5213, 321.3875)
        blue_goal_target = Vec3(0, -5213, 321.3875)
    
        
        # Test if team is orange
        if current_team == 1:
            target_location = orange_goal_target
        else:
            target_location = blue_goal_target
            

        if car_location.dist(target_location) > 1500:
            controls = SimpleControllerState()
            controls.steer = steer_toward_target(my_car, target_location)
            controls.throttle = 1.0

        if car_location.dist(target_location) == car_location:
            controls.throttle = 0
            
           

    
        

        return controls

 