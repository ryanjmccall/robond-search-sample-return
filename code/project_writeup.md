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
In the Jupyter Notebook `Rover_Project_Test_Notebook` I ran the first several functions to view the image data I had recorded from the 'roversim' 
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

I completed the `process_image()` function by chaining together the perspective transform and color threshold with a function 
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

For the `decision_step()` function I made one change to the decision tree. I added a case to slowly approach a rock in 'stop'
mode. In this case we perform the following: 

```
Rover.throttle = 0.1
Rover.brake = 0
Rover.steer = np.clip(np.mean(Rover.rock_angles * 180 / np.pi), -15, 15)
```

Initially the rover was not able to avoid dead-ends and turn from boundaries very well, so I made some parameter adjustments to make
it more sensitive and repsonsive to boundaries / walls. Here are the specific changes:

- Increased `throttle_set` from 0.2 to 2 for faster movement without much loss of performance
- Increased `brake_set` from 10 to 50 to more quickly stop for obstacles
- Increased `stop_forward` from 50 to 500 pixels to help make the rover stop more readily before it crashes into walls 
- Increase `go_forward` from 500 to 600 to ensure the robot does not stay stuck in a 4-wheel turn
- Decreased `max_vel` from 2.0 to 1.75 to have a better chance of stopping before obstacles
 
 
#### 2. Launching in autonomous mode your rover can navigate and map autonomously.  Explain your results and how you might improve them in your writeup.  

When running the simulator I used a screen resolution of 1280 x 720 and a graphics quality of 'Good'. The frames per second measure was typically around 36-37.
For the limited trial lengths I had to work with I was able to test with I was able to achieve around 77% mapping fidelity 
and at least 40% mapped terrain. The rover was proficient at detecting rock samples. In general I felt the perception 
algorithm was sufficient for the task, while the decision algorithm could add some additional cases to implement rock sample 
retrieval. Currently, the rover will only approach rocks at very low speeds. If I wanted to improve the rover I would think 
about how to add decision tree cases that move the robot toward the rock samples without hampering previously mentioned 
performance measures and getting the rover stuck on obstacles.

Please see `output/roversim_recording.mp4` for a recording of the rover meeting the basic objectives.

#### Attribution
While developing this project I drew upon ideas presented in the `Rover Project Walkthrough Stereo` video. In particular
 I used the image mask technique for obstacle mapping and the rock filtering threshold values described therein.
