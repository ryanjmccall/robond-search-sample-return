import numpy as np


# increase amount of steering
STEER_BOOST_FACTOR = 1

# smooth / slow the rate of change of steering angle
STEER_TO_IDEAL_RATIO = 0.25


def smoothSteer(Rover):
    # Set steering to average angle clipped to the range +/- 15
    idealSteerAngle = np.clip(np.mean(Rover.nav_angles * 180 / np.pi) * STEER_BOOST_FACTOR, -15, 15)

    # Make a partial transition to ideal steer angle
    Rover.steer += STEER_TO_IDEAL_RATIO * idealSteerAngle


def isRock(Rover):
    return Rover.rock_angles is not None and Rover.rock_angles.any()


def smoothDecreaseToZero(value, factor=0.9):
    """Gradually decrease value towards 0"""
    return value * factor


# This is where you can build a decision tree for determining throttle, brake and steer 
# commands based on the output of the perception_step() function
def decision_step(Rover):
    # Implement conditionals to decide what to do given perception data
    # Here you're all set up with some basic functionality but you'll need to
    # improve on this decision tree to do a good job of navigating autonomously!

    # Example:
    # Check if we have vision data to make decisions with
    if Rover.nav_angles is not None:
        # the mean steer angle is where we want to go
        idealSteerAngle = np.mean(Rover.nav_angles * 180 / np.pi)
        # print("*** IDEAL STEER %s" % idealSteerAngle)

        # only focus on steer angles when their abs value is less than this threshold
        forwardAngleThreshold = 14

        # Check for Rover.mode status
        if Rover.mode == 'forward':
            if abs(idealSteerAngle) > forwardAngleThreshold:
                # The idea of this condition is that first and foremost, the rover should keep turning
                #  if there is an obstacle directly in front.  The brake is off, the throttle is not touched, and
                # steering is performed.
                Rover.brake = 0
                smoothSteer(Rover)

            elif len(Rover.nav_angles) < Rover.stop_forward:
                # If there's a lack of navigable terrain pixels then go to 'stop' mode
                print("3a - Stop in forward-mode")

                # Set mode to "stop" and hit the brakes!
                Rover.throttle = 0
                # Set brake to stored brake value
                Rover.brake = Rover.brake_set
                Rover.steer = smoothDecreaseToZero(Rover.steer)
                Rover.mode = 'stop'

            elif len(Rover.nav_angles) >= Rover.stop_forward:
                # Check the extent of navigable terrain
                # If mode is forward, navigable terrain looks good
                # and velocity is below max, then throttle
                if Rover.vel < Rover.max_vel:
                    # Set throttle value to throttle setting
                    # print("2 - Accelerating forward-mode")
                    Rover.throttle = Rover.throttle_set
                else: # Else coast
                    # print("1 - Top-speed forward-mode")
                    Rover.throttle = 0

                Rover.brake = 0
                smoothSteer(Rover)

        # If we're already in "stop" mode then make different decisions
        elif Rover.mode == 'stop':
            # If we're in stop mode but still moving keep braking
            if Rover.vel > 0.2:
                print("3b - Stop in stop-mode")
                Rover.throttle = 0
                Rover.brake = Rover.brake_set
                Rover.steer = smoothDecreaseToZero(Rover.steer)
            # If we're not moving (vel < 0.2) then do something else
            elif Rover.vel <= 0.2:
                if isRock(Rover):
                    print("9 From stop; turn to rock")
                    Rover.throttle = 0
                    # Release the brake to allow turning
                    Rover.brake = 0
                    Rover.steer = np.clip(np.mean(Rover.rock_angles * 180 / np.pi), -15, 15)

                # Now we're stopped and we have vision data to see if there's a path forward
                elif len(Rover.nav_angles) < Rover.go_forward or abs(idealSteerAngle) >= forwardAngleThreshold:
                    # print("5 - 4-wheel turn")
                    Rover.throttle = 0
                    # Release the brake to allow turning
                    Rover.brake = 0
                    # Turn range is +/- 15 degrees, when stopped the next line will induce 4-wheel turning
                    Rover.steer = -15

                elif len(Rover.nav_angles) >= Rover.go_forward and abs(idealSteerAngle) < forwardAngleThreshold:
                    # If we're stopped but see sufficient navigable terrain in front then go!
                    # print("4 - From stop; Accelerate")
                    # Set throttle back to stored value
                    Rover.throttle = Rover.throttle_set
                    # Release the brake
                    Rover.brake = 0
                    # steer towards mean angle
                    smoothSteer(Rover)
                    Rover.mode = 'forward'

    # Just to make the rover do something 
    # even if no modifications have been made to the code
    else:
        print("6 - Default")
        Rover.throttle = Rover.throttle_set
        Rover.steer = smoothDecreaseToZero(Rover.steer)
        Rover.brake = 0
        
    # If in a state where want to pickup a rock send pickup command
    if Rover.near_sample and Rover.vel == 0 and not Rover.picking_up:
        Rover.send_pickup = True
    
    return Rover
