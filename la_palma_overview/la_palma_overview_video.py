# -*- encoding:utf-8 -*-
"""
Makes nightly summary videos of the Roque Observatry on La Palma.
A FACT like folder structure is created for each new night, e.g.
yyyy/mm/nn (nn is night here, a new night is created 12:00).
During the night, each minute an la_palma_overview image is saved to the 
directory of the current night.
In the morning, the image sequence is converted to a video.
This nightly cycle will go on forever.
If the process is interrupted, it can continue the imagesequence with the 
correct numbering at any time.

Usage: la_palma_overview_video [-o=OUTPUT_PATH] [-w=WORKING_PATH] [-t]

Options:
    -o --output=OUTPUT_PATH           path to save the output videos
    -w --working_path=WORKING_PATH    path to save the raw image sequences
    -t --trash_images                 trash image sequence after creating video
"""
from __future__ import print_function, absolute_import

__all__ = ['make_video_from_images', 'la_palma_overview_video']

import docopt
import la_palma_overview as lpo
from datetime import datetime, timedelta
import time
import os, glob
import numpy as np
import send2trash as s2t
from subprocess import call

def night_delay(now):
    return now - timedelta(hours=12)

def current_year(now):
    return night_delay(now).strftime("%Y")

def current_month(now):
    return night_delay(now).strftime("%m")

def current_night(now):
    return night_delay(now).strftime("%d")

def next_index_for_image_in_night(path2night):
    image_pattern = os.path.join(path2night, "*.jpg")
    indices = []
    for image_name in glob.glob(image_pattern):
        image_index = image_name[-10:-4]
        indices.append(int(image_index))
    if len(indices) == 0:
        return '0'.zfill(6)
    indices = np.array(indices)
    return str(indices.max() + 1).zfill(6)

def already_tried_to_create_video(path2night):
    return os.path.exists(os.path.join(path2night, 'avconv_stdout.txt'))

def trash_image_sequence_in(path2night):
    for image in glob.glob(os.path.join(path2night, '*.jpg')):
        s2t.send2trash(image)

def make_video_from_images(path2night, video_path):
    """
    Makes a video from sequence of jpg images.
    The input image names must be formatted like: '%06d.jpg', e.g. 000123.jpg.
    The numbering of the image filenames must be a sequence.
    Next to the output video, also the stdout and stderr of the avconv 
    call is saved.
    The video quality is set to be a good compromise for the la_palma_overview
    images. The video format is h264 mp4 and the resolution is 1920x1080 with 
    12fps.

    Parameters
    ----------
    path2night : string
        Path to the directory containing the image sequence

    video_path : string
        Path to the output video file. Also the stdout and stderr of avconv
        is witten there.

    Dependencies
    ------------
    Needs avconv from libav
    """
    avconv_command = [
        'avconv',
        '-y', # force overwriting of existing output file 
        '-framerate', '12', # 12 Frames per second
        '-f', 'image2', 
        '-i', os.path.join(path2night,'%06d.jpg'), 
        '-c:v', 'h264',
        '-s', '1920x1080', # sample images down to FullHD 1080p
        '-crf', '23', # high quality 0 (best) to 53 (worst)
        '-crf_max', '25', # worst quality allowed
        video_path
    ]
    avconv_stdout = open(os.path.join(path2night, 'avconv_stdout.txt'), 'w')
    avconv_stderr = open(os.path.join(path2night, 'avconv_stderr.txt'), 'w')
    avconv_return_value = call(avconv_command, stdout=avconv_stdout, stderr=avconv_stderr)
    avconv_stdout.close()
    avconv_stderr.close()
    return avconv_return_value

def logg_time(now):
    return now.strftime("%Y %m %d %H:%M")

class VideoStopWatch(object):
    def __init__(self, path2night):
        self.__start_video_convert = datetime.utcnow()
        print(logg_time(self.__start_video_convert), "Create video from images in", path2night)
    
    def stop(self):
        end_video_convert = datetime.utcnow()
        time_to_convert = end_video_convert - self.__start_video_convert
        print(logg_time(end_video_convert), "Video is done. Took", time_to_convert.seconds, "seconds to convert.")
                       

def la_palma_overview_video(output_path=None, working_path=None, trash_images=False):
    """
    Makes nightly summary videos of the Roque Observatry on La Palma.
    A FACT like folder structure is created for each new night, e.g.
    yyyy/mm/nn (nn is night here, a new night is created 12:00).
    During the night, each minute an la_palma_overview image is saved to the 
    directory of the current night.
    In the morning, the image sequence is converted to a video.
    This nightly cycle will go on forever.
    If the process is interrupted, it can continue the imagesequence with the 
    correct numbering at any time. 

    Parameters
    ----------
    output_patht : string [optional]
        Directory to save the final video to.
        Default is the working_path.

    working_path : string [optional]
        Directory to collect raw image sequences in.
        Default is the current working directory.

    trash_images : bool [optional]
        Moves the raw image sequence to the trash after the video is created.

    Dependencies
    ------------
    avconv from libav
    """
    if working_path is None:
        working_path = os.getcwd()

    if output_path is None:
        output_path = working_path

    while True:
        now = datetime.utcnow()

        year = current_year(now)
        path2year = os.path.join(working_path, year)
        if not os.path.exists(path2year):
            os.mkdir(path2year)
        month = current_month(now)
        path2month = os.path.join(path2year, month)
        if not os.path.exists(path2month):
            os.mkdir(path2month)
        night = current_night(now)
        path2night = os.path.join(path2month, night)
        if not os.path.exists(path2night):
            os.mkdir(path2night)

        if 17 <= now.hour < 24 or 0 <= now.hour < 7:
            index = next_index_for_image_in_night(path2night)
            image_name = index+".jpg"
            path2image = os.path.join(path2night, image_name)
            lpo.save_image(path2image)
            print(logg_time(now), "Save image", path2image)
        else:
            if now.hour < 12:
                if already_tried_to_create_video(path2night):
                    print(logg_time(now), "Waiting for next night...")
                else:
                    video_path = output_path
                    if output_path == working_path:
                        video_path = path2night

                    timer = VideoStopWatch(path2night)
                    video_maker_return_code = make_video_from_images(
                        path2night,
                        os.path.join(video_path, year+month+night+'.mp4')
                    )
                    timer.stop()
                    if video_maker_return_code == 0 and trash_images:
                        trash_image_sequence_in(path2night)
            else:
                print(logg_time(now), "Waiting for next night...")
        time.sleep(60)

def main():
    try:
        arguments = docopt.docopt(__doc__)
        la_palma_overview_video(
            output_path=arguments['--output'], 
            working_path=arguments['--working_path'],
            trash_images=arguments['--trash_images']
        )

    except docopt.DocoptExit as e:
        print(e)

if __name__ == "__main__":
    main()
