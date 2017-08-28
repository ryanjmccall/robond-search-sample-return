import numpy as np
import cv2


# Identify pixels above the threshold
# Threshold of RGB > 160 does a nice job of identifying ground pixels only
def color_thresh(img, rgb_thresh=(160, 160, 160)):
    # Create an array of zeros same xy size as img, but single channel
    color_select = np.zeros_like(img[:,:,0])
    # Require that each pixel be above all three threshold values in RGB
    # above_thresh will now contain a boolean array with "True"
    # where threshold was met
    above_thresh = (img[:,:,0] > rgb_thresh[0]) \
                & (img[:,:,1] > rgb_thresh[1]) \
                & (img[:,:,2] > rgb_thresh[2])
    # Index the array of zeros with the boolean array and set to 1
    color_select[above_thresh] = 1
    # Return the binary image
    return color_select


def rock_thresh(img, levels=(110, 110, 50)):
    color_select = np.zeros_like(img[:,:,0])
    rockpix = ((img[:,:,0] > levels[0]) & (img[:,:,1] > levels[1]) & (img[:,:,2] < levels[2]))
    color_select[rockpix] = 1
    return color_select


# Define a function to convert from image coords to rover coords
def  rover_coords(binary_img):
    # Identify nonzero pixels
    ypos, xpos = binary_img.nonzero()
    # Calculate pixel positions with reference to the rover position being at the 
    # center bottom of the image.  
    x_pixel = -(ypos - binary_img.shape[0]).astype(np.float)
    y_pixel = -(xpos - binary_img.shape[1]/2 ).astype(np.float)
    return x_pixel, y_pixel


# Define a function to convert to radial coords in rover space
def to_polar_coords(x_pixel, y_pixel):
    # Convert (x_pixel, y_pixel) to (distance, angle) 
    # in polar coordinates in rover space
    # Calculate distance to each pixel
    dist = np.sqrt(x_pixel**2 + y_pixel**2)
    # Calculate angle away from vertical for each pixel
    angles = np.arctan2(y_pixel, x_pixel)
    return dist, angles

# Define a function to map rover space pixels to world space
def rotate_pix(xpix, ypix, yaw):
    # Convert yaw to radians
    yaw_rad = yaw * np.pi / 180
    xpix_rotated = (xpix * np.cos(yaw_rad)) - (ypix * np.sin(yaw_rad))
                            
    ypix_rotated = (xpix * np.sin(yaw_rad)) + (ypix * np.cos(yaw_rad))
    # Return the result  
    return xpix_rotated, ypix_rotated

def translate_pix(xpix_rot, ypix_rot, xpos, ypos, scale): 
    # Apply a scaling and a translation
    xpix_translated = (xpix_rot / scale) + xpos
    ypix_translated = (ypix_rot / scale) + ypos
    # Return the result  
    return xpix_translated, ypix_translated


# Define a function to apply rotation and translation (and clipping)
# Once you define the two functions above this function should work
def pix_to_world(xpix, ypix, xpos, ypos, yaw, world_size, scale):
    # Apply rotation
    xpix_rot, ypix_rot = rotate_pix(xpix, ypix, yaw)
    # Apply translation
    xpix_tran, ypix_tran = translate_pix(xpix_rot, ypix_rot, xpos, ypos, scale)
    # Perform rotation, translation and clipping all at once
    x_pix_world = np.clip(np.int_(xpix_tran), 0, world_size - 1)
    y_pix_world = np.clip(np.int_(ypix_tran), 0, world_size - 1)
    # Return the result
    return x_pix_world, y_pix_world

# Define a function to perform a perspective transform
def perspect_transform(img, src, dst):
    M = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(img, M, (img.shape[1], img.shape[0]))  # keep same size as input image
    mask = cv2.warpPerspective(np.ones_like(img[:,:,0]), M, (img.shape[1], img.shape[0]))
    return warped, mask


def perception_step(Rover):
    image = Rover.img

    # Define calibration box in source (actual) and destination (desired) coordinates
    # These source and destination points are defined to warp the image
    # to a grid where each 10x10 pixel square represents 1 square meter
    dst_size = 5
    # Set a bottom offset to account for the fact that the bottom of the image
    # is not the position of the rover but a bit in front of it
    bottom_offset = 6

    world_size = Rover.worldmap.shape[0]
    worldScale = 2 * dst_size

    # 1) Define source and destination points for perspective transform
    # 2) Apply perspective transform
    source = np.float32([[14, 140], [301, 140], [200, 96], [118, 96]])
    destination = np.float32([[image.shape[1] / 2 - dst_size, image.shape[0] - bottom_offset],
                              [image.shape[1] / 2 + dst_size, image.shape[0] - bottom_offset],
                              [image.shape[1] / 2 + dst_size, image.shape[0] - 2 * dst_size - bottom_offset],
                              [image.shape[1] / 2 - dst_size, image.shape[0] - 2 * dst_size - bottom_offset],
                              ])
    warped, mask = perspect_transform(image, source, destination)

    # 3) Apply color threshold to identify navigable terrain/obstacles/rock samples
    navigableMap = color_thresh(warped)

    # obstacle map is opposite / inverse of navigable area filtered / truncated by the mask
    obstacleMap = np.absolute(np.float32(navigableMap) - 1) * mask

    # 4) Update Rover.vision_image (this will be displayed on left side of screen)
    # Channels: 0 - obstacle, 1 - rock, 2 - navigable
    Rover.vision_image[:,:,0] = obstacleMap * 255
    Rover.vision_image[:,:,2] = navigableMap * 255

    # 5) Convert map image pixel values to rover-centric coords
    navigableXPix, navigableYPix = rover_coords(navigableMap)
    obstacleXPix, obstacleYPix = rover_coords(obstacleMap)

    # 6) Convert rover-centric pixel values to world coordinates
    navXWorld, navYWorld = pix_to_world(navigableXPix, navigableYPix, Rover.pos[0], Rover.pos[1], Rover.yaw, world_size,
                                        worldScale)
    obs_x_world, obs_y_world = pix_to_world(obstacleXPix, obstacleYPix, Rover.pos[0], Rover.pos[1], Rover.yaw,
                                            world_size, worldScale)

    # 7) Update Rover worldmap (to be displayed on right side of screen)
        # Example: Rover.worldmap[obstacle_y_world, obstacle_x_world, 0] += 1
        #          Rover.worldmap[rock_y_world, rock_x_world, 1] += 1
        #          Rover.worldmap[navigable_y_world, navigable_x_world, 2] += 1

    # correct for small rounding errors
    if Rover.roll < 0:
        Rover.roll = 0

    if Rover.pitch < 0:
        Rover.pitch = 0

    # ignore input when rover is unstable
    CHOPPY_LOWER_BOUND = 0.5
    CHOPPY_UPPER_BOUND = 359.5
    if (CHOPPY_LOWER_BOUND < Rover.roll < CHOPPY_UPPER_BOUND) or (CHOPPY_LOWER_BOUND < Rover.pitch < CHOPPY_UPPER_BOUND):
        # print("*** too choppy: pitch %s roll %s" % (Rover.pitch, Rover.roll))
        pass
    else:
        Rover.worldmap[obs_y_world, obs_x_world, 0] += 1
        Rover.worldmap[navYWorld, navXWorld, 2] += 10

    # 8) Convert rover-centric pixel positions to polar coordinates
    Rover.nav_dists, Rover.nav_angles = to_polar_coords(navigableXPix, navigableYPix)
    rock_map = rock_thresh(warped, levels=(110, 110, 50))  # get binary rock map image
    if rock_map.any():
        Rover.vision_image[:, :, 1] = rock_map * 255

        rock_x, rock_y = rover_coords(rock_map)
        rock_x_world, rock_y_world = pix_to_world(rock_x, rock_y, Rover.pos[0], Rover.pos[1], Rover.yaw, world_size,
                                                  worldScale)

        Rover.rock_dists, Rover.rock_angles = to_polar_coords(rock_x, rock_y)

        # Select closest rock distance
        rock_idx = np.argmin(Rover.rock_dists)

        # Set pixel point white in world map of closest rock point
        rock_xcen = rock_x_world[rock_idx]
        rock_ycen = rock_y_world[rock_idx]
        Rover.worldmap[rock_ycen, rock_xcen, 1] = 255
    else:
        Rover.vision_image[:, :, 1] = 0
    
    return Rover
