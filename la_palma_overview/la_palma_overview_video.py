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
    --start-time=<time>    Hour of UTC time before no images are downloaded [default: 17]
    --dummy                Create ten images, then the video. Useful for testing this script.
    -t, --trash-images     Move images to trash after successfull video creation
    -v, --verbose          More verbose log output
    -l <f>, --logfile=<f>  If given, log also to file
'''
import docopt
from datetime import datetime, timedelta
import time
import os
import glob
import numpy as np
import send2trash as s2t
from subprocess import call
import logging

from . import save_image
from .log import setup_logging


__all__ = ['make_video_from_images', 'la_palma_overview_video']


log = logging.getLogger('la_palma_overview')


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
    return os.path.exists(os.path.join(video_dir, 'ffmpeg_stdout.txt'))


def trash_image_sequence_in(image_path):
    for image in glob.glob(os.path.join(image_path, '*.jpg')):
        s2t.send2trash(image)


def make_video_from_images(image_path, video_path):
    '''
    Makes a video from sequence of jpg images.
    The input image names must be formatted like: '%06d.jpg', e.g. 000123.jpg.
    The numbering of the image filenames must be a sequence.
    Next to the output video, also the stdout and stderr of the ffmpeg
    call is saved.
    The video quality is set to be a good compromise for the la_palma_overview
    images. The video format is h264 mp4 and the resolution is 1920x1080 with
    12fps.

    Parameters
    ----------
    image_path : string
        Path to the directory containing the image sequence

    video_path : string
        Path to the output video file. Also the stdout and stderr of ffmpeg
        is witten there.

    Dependencies
    ------------
    Needs ffmpeg from libav
    '''
    video_dir = os.path.dirname(video_path)
    ffmpeg_command = [
        'ffmpeg',
        '-y',                # force overwriting of existing output file
        '-framerate', '12',  # 12 Frames per second
        '-i',  os.path.join(image_path, '%06d.jpg'),
        '-c:v', 'libx264',
        '-s', '1920x1080',    # sample images down to FullHD 1080p
        '-pix_fmt', 'yuv420p',
        '-preset', 'slower',  # better compression
        '-crf', '23',         # high quality 0 (best) to 53 (worst)
        '-crf_max', '25',     # worst quality allowed
        video_path
    ]
    outpath = os.path.join(video_dir, 'ffmpeg_stdout.txt')
    errpath = os.path.join(video_dir, 'ffmpeg_stderr.txt')
    with open(outpath, 'w') as stdout, open(errpath, 'w') as stderr:
        ffmpeg_return_value = call(ffmpeg_command, stdout=stdout, stderr=stderr)

    return ffmpeg_return_value


def date_path(date, base='', subdir=''):
    return os.path.join(
        base,
        '{:04d}'.format(date.year),
        '{:02d}'.format(date.month),
        '{:02d}'.format(date.day),
        subdir,
    )


def save_image_to_date_path(base='', subdir=''):
    night = current_night()

    output_dir = date_path(night, base=base, subdir=subdir)
    os.makedirs(output_dir, exist_ok=True)

    index = next_index_for_image_in_night(output_dir)
    image_name = index + '.jpg'

    output_path = os.path.join(output_dir, image_name)

    save_image(output_path)


def save_video_to_date_path(
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

    video_path = os.path.join(output_dir, night_string + '.mp4')

    image_path = date_path(night, base=image_base, subdir=image_subdir)

    if already_tried_to_create_video(output_dir):
        log.info('Video already created, skipping')
    else:
        before_video = datetime.utcnow()
        video_maker_return_code = make_video_from_images(
            image_path,
            video_path,
        )
        duration = (datetime.utcnow() - before_video).total_seconds()
        if video_maker_return_code == 0:
            log.info('Video {} created succesfully'.format(video_path))
            log.info('Video creation took {} s'.format(duration))
            if trash_images is True:
                trash_image_sequence_in(image_path)


def la_palma_overview_video(
        video_base=None,
        video_subdir='',
        image_base=None,
        image_subdir='images',
        trash_images=False,
        start_time=17,
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
    ffmpeg
    '''

    video_base = video_base or os.getcwd()
    image_base = image_base or os.getcwd()

    while True:
        now = datetime.utcnow()
        if now.hour >= start_time or now.hour <= 7:
            log.info('Getting image')
            save_image_to_date_path(image_base, image_subdir)
            log.info('done')
        else:
            if now.hour < 12:
                save_video_to_date_path(
                    video_base,
                    video_subdir,
                    image_base,
                    image_subdir,
                    trash_images=trash_images,
                )
            else:
                log.info('Waiting for next night')

        time.sleep(60)


def la_palma_overview_video_dummy(
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
    ffmpeg
    '''

    video_base = video_base or os.getcwd()
    image_base = image_base or os.getcwd()

    N = 10
    for i in range(N):
        log.info(f'Getting image {i} of {N}')
        save_image_to_date_path(image_base, image_subdir)
        log.info('done')

    save_video_to_date_path(
        video_base,
        video_subdir,
        image_base,
        image_subdir,
        trash_images=trash_images,
    )


def main():
    try:
        arguments = docopt.docopt(__doc__)
        setup_logging(arguments['--logfile'], arguments['--verbose'])

        if not arguments['--dummy']:
            la_palma_overview_video(
                video_base=arguments['--video-base'],
                video_subdir=arguments['--video-subdir'],
                image_base=arguments['--image-base'],
                image_subdir=arguments['--image-subdir'],
                trash_images=arguments['--trash-images'],
                start_time=int(arguments['--start-time']),
            )
        else:
            la_palma_overview_video_dummy(
                video_base=arguments['--video-base'],
                video_subdir=arguments['--video-subdir'],
                image_base=arguments['--image-base'],
                image_subdir=arguments['--image-subdir'],
                trash_images=arguments['--trash-images'],
            )

    except docopt.DocoptExit as e:
        print(e)


if __name__ == "__main__":
    main()
