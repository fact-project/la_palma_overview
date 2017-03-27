#!/usr/bin/env python
'''
Creates an overview image of Canary island La Palma, Roque de los Muchachos.

Usage: la_palma_overview [options]

Options:
    -o --output=OUTPUT_PATH     path to write the output image
    -v --verbose                tell what is currently done
    -l <f>, --logfile=<f>  If given, log also to file

Notes:
    - When output is not specified, a time stamp image name is created:
      'la_palma_yyyymmdd_HHMMSS.jpg'
    - A UTC time stamp and the FACT telescope status are put into the image.
'''
import docopt
import skimage
import skimage.io
import skimage.transform
import skimage.color
import io
import datetime as dt
import numpy as np
import smart_fact_crawler as sfc
import requests
import logging
from PIL import Image, ImageDraw, ImageFont

from multiprocessing.pool import ThreadPool

from .log import setup_logging


__all__ = ['save_image']


log = logging.getLogger('la_palma_overview')


def empty_image(rows, cols):
    return np.zeros(shape=(rows, cols, 3), dtype='uint8')


def clock2img(rows, cols):

    img = Image.new('RGB', (cols, rows))

    font_time = ImageFont.truetype('DejaVuSansMono.ttf', size=120)
    font_date = ImageFont.truetype('DejaVuSansMono.ttf', size=100)
    font_run = ImageFont.truetype('DejaVuSansMono.ttf', size=120)

    d = ImageDraw.Draw(img)

    now = dt.datetime.utcnow()

    time = now.strftime('%H:%M:%S')
    date = now.strftime('%Y-%m-%d')

    w, h = d.textsize(time, font=font_time)
    d.text(
        ((cols - w) / 2, 0),
        time,
        font=font_time,
        fill='red'
    )

    w, h = d.textsize(date, font=font_date)
    d.text(
        ((cols - w) / 2, (rows - h) / 2),
        date,
        font=font_date,
        anchor='center',
        align='center',
        fill='red'
    )
    try:
        runs = sfc.observations(fallback=True).runs

        if runs is not None:
            last_run = runs[-1]
            if (dt.datetime.utcnow() - last_run.start) <= dt.timedelta(minutes=15):
                run_str = 'Run {0: 3d}'.format(last_run.id)
                w, h = d.textsize(run_str, font=font_run)
                d.text(
                    ((cols - w) / 2, rows - h - 10),
                    run_str,
                    font=font_run,
                    anchor='top',
                    fill='red'
                )

    except Exception as e:
        log.exception("Could't get run_id.")

    return np.array(img, dtype='uint8')


def smart_fact2img(rows, cols):
    currents = sfc.sipm_currents()
    drive_pointing = sfc.drive_pointing()
    weather = sfc.weather()
    rel_temp = sfc.camera_climate().relative_temperature_mean.value
    cam_temp = rel_temp + weather.temperature.value

    status_text = (
        'SQM\n'
        ' Magnitude..{Magnitude: > 6.1f}\n'
        'SIPM\n'
        ' min........{min_cur: > 6.1f} {cur_unit}\n'
        ' med........{med_cur: > 6.1f} {cur_unit}\n'
        ' max........{max_cur: > 6.1f} {cur_unit}\n'
        'Temp\n'
        ' outside....{out_temp: > 6.1f} C\n'
        ' container..{cont_temp: > 6.1f} C\n'
        ' camera.....{cam_temp: > 6.1f} C\n'
        'Pointing: {source_name}\n'
        ' Azimuth....{source_az: > 6.1f} {source_az_unit}\n'
        ' Zenith.....{source_zd: > 6.1f} {source_zd_unit}\n'
    ).format(
        Magnitude=sfc.sqm().magnitude.value,
        power=currents.power_camera.value,
        power_unit=currents.power_camera.unit,
        min_cur=currents.min_per_sipm.value,
        med_cur=currents.median_per_sipm.value,
        max_cur=currents.max_per_sipm.value,
        cur_unit=currents.max_per_sipm.unit,
        out_temp=weather.temperature.value,
        cont_temp=float(sfc.container_temperature().current.value),
        cam_temp=cam_temp,
        source_name=sfc.current_source().name,
        source_az=drive_pointing.azimuth.value,
        source_zd=drive_pointing.zenith_distance.value,
        source_az_unit=drive_pointing.azimuth.unit,
        source_zd_unit=drive_pointing.zenith_distance.unit,
    )

    img = Image.new('RGB', (cols, rows))
    font = ImageFont.truetype('DejaVuSansMono.ttf', size=32)

    d = ImageDraw.Draw(img)

    d.text((10, 10), status_text, font=font, anchor='top', fill='red')

    return np.array(img, dtype='uint8')


def stack_image_list_into_rows_and_cols(imgs, big_rows, big_cols):

    rows = imgs[0].shape[0]
    cols = imgs[0].shape[1]

    col_stack = np.zeros(shape=(0, big_cols * cols, 3), dtype='uint8')

    for row in range(big_rows):

        row_stack = np.zeros(shape=(rows, 0, 3), dtype='uint8')

        for col in range(big_cols):
            i = col + big_cols*row

            if i < len(imgs):
                row_stack = np.hstack((row_stack, imgs[i]))
            else:
                row_stack = np.hstack((row_stack, empty_image(rows, cols)))

        col_stack = np.vstack((col_stack, row_stack))

    return col_stack


def download_and_resize_image(url, rows, cols, fmt='jpg', fallback=True):
    '''
    Download image at url.
    Resize to size cols x rows
    if fallback is True, a black image is returned in case
    the request fails, else an exception is raised
    '''
    try:
        req = requests.get(url, verify=False, timeout=15)

        img = skimage.io.imread(io.BytesIO(req.content), format=fmt)

        if img.ndim == 2:
            img = skimage.color.gray2rgb(img)

        img = skimage.transform.resize(img, (rows, cols))
        img = (img * 255).astype('uint8')

        log.debug('Downloaded image from url {}'.format(url))

    except Exception as e:
        if fallback is True:
            log.exception('Failed to get image for url {}'.format(url))
            img = empty_image(rows, cols)
        else:
            raise IOError from e

    return img


def save_image(output_path, overview_config=None):
    """
    Save an La Palma overview image with time stamp and FACT telescope info

    Parameters
    ----------
    output_patht : string [optional]
        path to save the final image
        When not specified, a time stamp image name is created:
        'la_palma_yyyymmdd_HHMMSS.jpg'

    verbose : bool [optional]
        tell what I am doing

    overview_config : dictonary [optional]
        specify the image urls and image resolutions yourself, further choose
        image stacking layout. Empty rows or columns are filled with black image
        tiles. It shall look like this:

        overview_config = {
            'img': {'rows': 480, 'cols': 640},
            'stacked_image': {'rows': 3, 'cols': 4},
            'image_urls': [
                'http://fact-project.org/cam/skycam.php',
                'http://www.gtc.iac.es/multimedia/netcam/camaraAllSky.jpg',
                'http://www.magic.iac.es/site/weather/AllSkyCurrentImage.JPG',
                'http://www.magic.iac.es/site/weather/can.jpg',
                'http://www.fact-project.org/cam/cam.php',
                'http://www.fact-project.org/cam/lidcam.php',
                'http://iris.not.iac.es/axis-cgi/jpg/image.cgi',
                'http://www.gtc.iac.es/multimedia/netcam/camaraExt.jpg',
                'http://www.magic.iac.es/site/weather/lastHUM6t.jpg',
                'http://www.magic.iac.es/site/weather/lastWPK6t.jpg'
            ]
        }
    """

    if output_path is None:
        output_path = dt.datetime.utcnow().strftime('la_palma_%Y%m%d_%H%M%S.jpg')

    cfg = overview_config
    if cfg is None:
        cfg = {
            'img': {'rows': 480, 'cols': 640},
            'stacked_image': {'rows': 3, 'cols': 4},
            'image_urls': [
                'http://fact-project.org/cam/skycam.php',
                'http://www.gtc.iac.es/multimedia/netcam/camaraAllSky.jpg',
                'http://www.magic.iac.es/site/weather/AllSkyCurrentImage.JPG',
                'http://www.magic.iac.es/site/weather/can.jpg',
                'http://www.fact-project.org/cam/cam.php',
                'http://www.fact-project.org/cam/lidcam.php',
                'http://iris.not.iac.es/axis-cgi/jpg/image.cgi',
                'http://www.tng.iac.es/webcam/get.html?resolution=640x480&compression=30&clock=1&date=1&dummy=1456393525188',
                # 'http://www.gtc.iac.es/multimedia/netcam/camaraExt.jpg',
                'http://www.magic.iac.es/site/weather/lastHUM6t.jpg',
                'http://www.magic.iac.es/site/weather/lastWPK6t.jpg'
            ]
        }

    # -----------------------------------
    # Collect all the images listed in the urls
    with ThreadPool(6) as pool:
        imgs = pool.map(
            lambda url: download_and_resize_image(
                url, cfg['img']['rows'], cfg['img']['cols']
            ),
            cfg['image_urls']
        )

    # -----------------------------------
    # Append a Smart FACT status image
    try:
        imgs.append(smart_fact2img(cfg['img']['rows'], cfg['img']['cols']))
        log.debug('Created smartfact imaged')
    except Exception as e:
        log.exception('Failed to get smartfact data')
        imgs.append(empty_image(cfg['img']['rows'], cfg['img']['cols']))

    # -----------------------------------
    # Append a time stamp image
    try:
        imgs.append(clock2img(cfg['img']['rows'], cfg['img']['cols']))
        log.debug('Created clock imaged')
    except Exception as e:
        log.exception('Failed to create clock image')
        imgs.append(empty_image(cfg['img']['rows'], cfg['img']['cols']))

    # -----------------------------------
    # create stacked image from list of single images
    image_stack = stack_image_list_into_rows_and_cols(
        imgs,
        cfg['stacked_image']['rows'],
        cfg['stacked_image']['cols']
    )

    # -----------------------------------
    # save the stacked image
    skimage.io.imsave(output_path, image_stack)


def main():
    try:
        arguments = docopt.docopt(__doc__)

        setup_logging(arguments['--logfile'], arguments['--verbose'])

        save_image(
            output_path=arguments['--output'],
        )
    except docopt.DocoptExit as e:
        print(e)


if __name__ == '__main__':
    main()
