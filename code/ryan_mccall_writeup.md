## Project: Search and Sample Return

---


**The goals / steps of this project are the following:**  

**Training / Calibration**  

* Download the simulator and take data in "Training Mode"
* Test out the functions in the Jupyter Notebook provided
* Add functions to detect obstacles and samples of interest (golden rocks)
* Fill in the `process_image()` function with the appropriate image processing steps (perspective transform, color threshold etc.) to get from raw images to a map.  The `output_image` you create in this step should demonstrate that your mapping pipeline works.
* Use `moviepy` to process the images in your saved dataset with the `process_image()` function.  Include the video you produce as part of your submission.

**Autonomous Navigation / Mapping**

* Fill in the `perception_step()` function within the `perception.py` script with the appropriate image processing functions to create a map and update `Rover()` data (similar to what you did with `process_image()` in the notebook). 
* Fill in the `decision_step()` function within the `decision.py` script with conditional statements that take into consideration the outputs of the `perception_step()` in deciding how to issue throttle, brake and steering commands. 
* Iterate on your perception and decision function until your rover does a reasonable (need to define metric) job of navigating and mapping.  

[//]: # (Image References)

[image1]: ../report_images/1_recorded_image.png
[image2]: ../report_images/2_transformed.png
[image3]: ../report_images/3_transformed_thresholded.png
[image4]: ../report_images/4_rock.png
[image5]: ../report_images/5_rock_tresh.png

## [Rubric](https://review.udacity.com/#!/rubrics/916/view) Points
### Here I will consider the rubric points individually and describe how I addressed each point in my implementation.  

---
### Writeup / README

#### 1. Provide a Writeup / README that includes all the rubric points and how you addressed each one.  You can submit your writeup as markdown or pdf.  

Please see the sections below for the project writeup.

### Notebook Analysis
#### 1. Run the functions provided in the notebook on test images (first with the test data provided, next on data you have recorded). Add/modify functions to allow for color selection of obstacles and rock samples.
In the Jupyter Notebook 'Rover_Project_Test_Notebook' I ran the first several functions to view the image data I had recorded from the 'roversim' 
simulator. Here is an example recorded image:


![sample recorded image][image1]


Next I defined the source and destination points in the image space for the perspective transform and applied the transformation.
Here is the same image as before transformed into top-down coordinates:


![transformed image][image2]


To identify the pixels that are navigable, I applied an RGB color threshold function requiring rgb values to be over the 
threshold: (160, 160, 160). The function outputs a binary image with 1 (rendered as white) representing the navigable terrain and 0 (as black)
representing obstacles or out of sight bounds.


![transformed-thresholded image][image3]


To identify rock samples, I defined a similar RGB threshold function to filter yellow pixels to "true" / 1 and others to "false" / 0. 
Specifically, the red channel must be greater than 110, green greater than 110, and blue less than 50.


![sample rock][image4]


Below is the result of applying the rock threshold to the previous image:


![rock threshold applied][image5]


#### 1. Populate the `process_image()` function with the appropriate analysis steps to map pixels identifying navigable terrain, obstacles and rock samples into a worldmap.  Run `process_image()` on your test data using the `moviepy` functions provided to create video output of your result. 

I completed the 'process_image()' function by chaining together the perspective transform and color threshold with a function 
to convert thresholded image pixels to rover-centric coordinates. With this, I then converted the pixel position to world-map coordinates.
For obstacles I incremented the worldmap channel 0 by 1, and, for navigable terrain, channel 2 by 10. I generated a 
video of recorded images that were processed by this function.
Please see `output/test_mapping.mp4` for the video.

### Autonomous Navigation and Mapping

#### 1. Fill in the `perception_step()` (at the bottom of the `perception.py` script) and `decision_step()` (in `decision.py`) functions in the autonomous mapping scripts and an explanation is provided in the writeup of how and why these functions were modified as they were.

For the `perception_step()` function I repeated much of the logic from the `process_image()` function. The first notable
deviation is the additional computation of a mask by the `perspect_transform` function. This mask contains 1s where the rover's
camera can see, and 0s elsewhere. The mask is used to help compute the obstacle map by marking the area out of the camera's
viewing angle as an obstacle. The next two differences arise due to the nature of the rover simulated world. Since the Rover's
roll and pitch can temporarily turn to small negative values, apparently due to rounding errors, I normalize these values to 0
if they are negative. Secondly, we know that the initial image perspective transform is only valid when the rover's roll and pitch are
stable, i.e., close to 0 (360) degrees. Thus, the perception step only updates the Rover's `worldmap` channels if these values
are in (0.5, 359.5) degrees. By ignoring input when the rover becomes "unstable," I was able to maintain acceptable (> 60%) fidelity of the 
visual updates to the worldmap.

Finally, the perception step includes several steps to update the world map when rock samples are detected. Specifically, using 
previously described rock-threshold function, I obtained a binary map of rock samples. If any rock pixels are detected I
transform them to rover coordinates, then to world coordinate, then to polar coordinates. Next I select the pixel that is closest
in polar distance and mark the corresponding pixel in world coordinates as white.

For the `decision_step()` function I made several alterations to achieve desirable performance. Broadly, I kept the general
format of the provided decision tree. However I tried to address the following problems I noticed with the default code:
1) using the mean polar angle of navigable pixels does not work when there are obstacles immediately ahead. For instances,
there can be many navigable pixels to the left and right, but if the rover goes straight, it will get stuck on rocks.
To remedy this, when I have vision data, I always compute the mean steer angle by:

`idealSteerAngle = np.mean(Rover.nav_angles * 180 / np.pi)`

However, I only make actions based on that angle when its absolute value is reasonably small. For this implementation I used 
the parameter:

`forwardAngleThreshold = 10`

to only go forward when the absolute value of the mean steer angle was 10 or less.

2) The rover was not able to avoid dead-ends and turn from boundaries very well, so I made some parameter adjustments to make
it more sensitive and repsonsive to boundaries / walls. In particular, when steering, I boosted the steering angle to that of 20 times the 
mean navigable polar angle (still clipping the result to [-15, 15]). Additionally, I made the following tweaks to the rover parameters:

- Increased `brake_set` from 10 to 50 to more quickly stop for obstacles

- Increased `stop_forward` from 50 to 500 pixels to help make the rover stop more readily before it crashes into walls 

- Decreased `max_vel` from 2.0 to 1.5 to have a better chance of stopping before obstacles

3) One final detail, when stopping, my general approach was to gradually decrease the steering angle by 10% each 
processing cycle so as to avoid chopping steering that can cause the rover to wobble.

Next I will address each decision tree path one-by-one:
1) `nav_angles` exist, mode="forward", `idealSteerAngle` > `forwardAngleThreshold`
The idea of this condition is that first and foremost, the rover should keep turning if there is an obstacle directly in front.
This case helps the rover from getting stuck on sharp edges. The brake is turned off, the throttle is not touched, and steering is performed.

2) `nav_angles` exist, mode="forward", `elif len(Rover.nav_angles) < Rover.stop_forward`
The idea here is that there is little navigable terrain ahead and its arrayed in a uniform fashion so we should enter 
stop mode and turn. Throttle is turned off, brake is set, steering angle is decreased by 10%, and mode is set to 'stop'.

3) `nav_angles` exist, mode="forward", `elif len(Rover.nav_angles) >= Rover.stop_forward`
Here, with open terrain ahead, we either maintain max velocity or accelerate by setting the throttle. The rover keeps up
 boosted steering.

4) `nav_angles` exist, mode="stop", `if Rover.vel > 0.2`
This case is to continue stopping if rover is still moving in stop mode.

5) `nav_angles` exist, mode="stop", `elif Rover.vel <= 0.2`, `if len(Rover.nav_angles) < Rover.go_forward or abs(idealSteerAngle) >= forwardAngleThreshold`
This case represents situations where the rover is stopped there is not much navigale space or the space is sharply off to the side.
 In this case I want the rover to perform a 4-wheel turn.
 
6) `nav_angles` exist, mode="stop", `elif len(Rover.nav_angles) >= Rover.go_forward and abs(idealSteerAngle) < forwardAngleThreshold`  
Only if there's sufficient navigable pixels straight ahead do I want the rover to leave 'stop' mode and enter 'forward' mode.

7) `nav_angles` do not exist
I changed the response to keep steering but not throttle or break. I'd rather the rover slow down and keep avoid obstacles.

#### 2. Launching in autonomous mode your rover can navigate and map autonomously.  Explain your results and how you might improve them in your writeup.  

When running the simulator I used a screen resolution of 1280 x 720 and a graphics quality of 'Good'. The frames per second measure was typically around 36-37.
I must note that I had some troubles with the python client disconnecting its communication from the Unity simulator. The 
disconnection appears to occur after about 1.5 minutes of running the simulation. I sought help on Slack and with 'Live help'
but was unable to ascertain the cause of the issue.

For the limited trial lengths I had to work with I was able to test with I was able to achieve around 79% mapping fidelity 
and at least 40% mapped terrain. The rover was proficient at detecting rock samples. In general I felt the perception 
algorithm was sufficient for the task, while the decision algorithm could add some additional cases to implement rock sample 
retrieval. Currently, the rover will only approach rocks by chance. If I wanted to improve the rover I would think 
about how to add decision tree cases that move the robot toward the rock samples without hampering previously mentioned 
performance measures.

Please see output/roversim_recording.mp4 for a recording of the rover meeting the basic objectives.
