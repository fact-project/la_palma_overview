# -*- encoding:utf-8 -*-
'''
Makes nightly summary videos of the Roque Observatry on La Palma.

A FACT like folder structure is created for each new night.

Single images are saved to <image-base>/YYYY/MM/NN/<image-subdir>,
Videos are saved to <video-base>/YYYY/MM/NN/<video-subdir>,
where NN is the date for a date switch at noon.

During the night, each minute an la_palma_overview image is saved to the
directory of the current night.
In the morning, the image sequence is converted to a video.
This nightly cycle will go on forever.
If the process is interrupted, it can continue the image sequence with the
correct numbering at any time.

Usage: la_palma_overview_video [options]

Options:
    --video-base=<dir>     Base directory for the videos
    --image-base=<dir>     Base directory for the images
    --video-subdir=<dir>   Subdirectory for the videos [default: ]
    --image-subdir=<dir>   Subdirectory for the images [default: images]
    -t, --trash-images     Move images to trash after successfull video creation
'''
import docopt
from datetime import datetime, timedelta
import time
import os
import glob
import numpy as np
import send2trash as s2t
from subprocess import call

import la_palma_overview as lpo


__all__ = ['make_video_from_images', 'la_palma_overview_video']


def current_night():
    return (datetime.utcnow() - timedelta(hours=12)).date()


def next_index_for_image_in_night(image_path):
    image_pattern = os.path.join(image_path, "*.jpg")
    indices = []
    for image_name in glob.glob(image_pattern):
        image_index = image_name[-10:-4]
        indices.append(int(image_index))
    if len(indices) == 0:
        return '0'.zfill(6)
    indices = np.array(indices)
    return str(indices.max() + 1).zfill(6)


def already_tried_to_create_video(video_dir):
    return os.path.exists(os.path.join(video_dir, 'avconv_stdout.txt'))


def trash_image_sequence_in(image_path):
    for image in glob.glob(os.path.join(image_path, '*.jpg')):
        s2t.send2trash(image)


def make_video_from_images(image_path, video_path):
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
    image_path : string
        Path to the directory containing the image sequence

    video_path : string
        Path to the output video file. Also the stdout and stderr of avconv
        is witten there.

    Dependencies
    ------------
    Needs avconv from libav
    """
    video_dir = os.path.dirname(video_path)
    avconv_command = [
        'avconv',
        '-y',                # force overwriting of existing output file
        '-framerate', '12',  # 12 Frames per second
        '-f', 'image2',
        '-i',  os.path.join(image_path, '%06d.jpg'),
        '-c:v', 'h264',
        '-s', '1920x1080',   # sample images down to FullHD 1080p
        '-crf', '23',        # high quality 0 (best) to 53 (worst)
        '-crf_max', '25',    # worst quality allowed
        video_path
    ]
    avconv_stdout = open(os.path.join(video_dir, 'avconv_stdout.txt'), 'w')
    avconv_stderr = open(os.path.join(video_dir, 'avconv_stderr.txt'), 'w')
    avconv_return_value = call(avconv_command, stdout=avconv_stdout, stderr=avconv_stderr)
    avconv_stdout.close()
    avconv_stderr.close()
    return avconv_return_value


def logg_time(now):
    return now.strftime("%Y %m %d %H:%M")


class VideoStopWatch(object):
    def __init__(self, image_path):
        self.__start_video_convert = datetime.utcnow()
        print(
            logg_time(self.__start_video_convert),
            "Create video from images in", image_path
        )

    def stop(self):
        end_video_convert = datetime.utcnow()
        time_to_convert = end_video_convert - self.__start_video_convert
        print(
            logg_time(end_video_convert),
            "Video is done. Took", time_to_convert.seconds, "seconds to convert."
        )


def date_path(date, base='', subdir=''):
    return os.path.join(
        base,
        str(date.year),
        str(date.month),
        str(date.day),
        subdir,
    )


def save_image(base='', subdir=''):
    night = current_night()

    output_dir = date_path(night, base=base, subdir=subdir)
    os.makedirs(output_dir, exist_ok=True)

    index = next_index_for_image_in_night(output_dir)
    image_name = index + '.jpg'

    output_path = os.path.join(output_dir, image_name)

    lpo.save_image(output_path)


def save_video(
        base='',
        subdir='',
        image_base='',
        image_subdir='',
        trash_images=False,
        ):
    night = current_night()
    night_string = night.strftime('%Y%m%d')

    output_dir = date_path(night, base=base, subdir=subdir)
    os.makedirs(output_dir, exist_ok=True)

    image_path = date_path(night, base=image_base, subdir=image_subdir)

    now = datetime.utcnow()
    if already_tried_to_create_video(output_dir):
        print(logg_time(now), 'Waiting for next night...')
    else:
        timer = VideoStopWatch(image_path)
        video_maker_return_code = make_video_from_images(
            image_path,
            os.path.join(output_dir, night_string + '.mp4')
        )
        timer.stop()
        if video_maker_return_code == 0 and trash_images is True:
            trash_image_sequence_in(image_path)


def la_palma_overview_video(
        video_base=None,
        video_subdir='',
        image_base=None,
        image_subdir='images',
        trash_images=False,
        ):
    '''
    Makes nightly summary videos of the Roque Observatry on La Palma.

    A FACT like folder structure is created for each new night, e.g.
    <base>/yyyy/mm/nn/<subdir> (nn is night here, a new night is created 12:00).

    During the night, each minute an la_palma_overview image is saved to the
    directory of the current night.
    In the morning, the image sequence is converted to a video.
    This nightly cycle will go on forever.

    If the process is interrupted, it can continue the image sequence with the
    correct numbering at any time.

    Parameters
    ----------
    video_base : string [optional]
        Base directory for the videos, YYYY/MM/DD structure is created from there
        Default is the the cwd

    video_subdir : string [optional]
        subdirectory after YYYY/MM/DD for the video, default is no subdirectory

    image_base : string [optional]
        Base directory for the images, YYYY/MM/DD structure is created from there
        Default is the the cwd

    image_subdir : string [optional]
        subdirectory after YYYY/MM/DD for the images, default is "images"

    trash_images : bool [optional]
        Moves the raw image sequence to the trash after the video is created.

    Dependencies
    ------------
    avconv from libav
    '''

    video_base = video_base or os.getcwd()
    image_base = image_base or os.getcwd()

    now = datetime.utcnow()
    while True:
        if now.hour >= 18 or now.hour <= 8:
            print('Getting image')
            save_image(image_base, image_subdir)
            print('done')

        else:
            if now.hour < 12:
                save_video(
                    video_base,
                    video_subdir,
                    image_base,
                    image_subdir,
                    trash_images=trash_images,
                )
            else:
                print(logg_time(now), 'Waiting for next night...')
        time.sleep(60)


def main():
    try:
        arguments = docopt.docopt(__doc__)
        print(arguments)
        la_palma_overview_video(
            video_base=arguments['--video-base'],
            video_subdir=arguments['--video-subdir'],
            image_base=arguments['--image-base'],
            image_subdir=arguments['--image-subdir'],
            trash_images=arguments['--trash-images']
        )

    except docopt.DocoptExit as e:
        print(e)


if __name__ == "__main__":
    main()
