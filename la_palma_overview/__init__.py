#!/usr/bin/env python
"""
Creates an overview image of Canary island La Palma, Roque de los Muchachos.

Usage: la_palma_overview [-o=OUTPUT_PATH] [-v]

Options:
    -o --output=OUTPUT_PATH     path to write the output image
    -v --verbose                tell what is currently done

Notes:
    - When output is not specified, a time stamp image name is created: 
      'la_palma_yyyymmdd_HHMMSS.jpg'
    - A UTC time stamp and the FACT telescope status are put into the image.
"""
from __future__ import absolute_import, print_function, division

__all__ = ['save_image']

import matplotlib
matplotlib.use('Agg') 
# Must be set to enforce matplotlib runs on machines 
# where no x server backend is specified
import docopt
import skimage
from skimage import io
from skimage import transform
import datetime as dt
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.font_manager import FontProperties
import io
import smart_fact_crawler as sfc
import glob
import sys
import requests

def empty_image(rows, cols):
    return np.zeros(shape=(rows,cols,3)).astype('uint8')

def clock2img(rows, cols):

    dpi = 96
    fig = plt.figure(figsize=(cols/dpi, rows/dpi), dpi=dpi)
    ax = plt.gca()
    ax.yaxis.set_visible(False)
    
    ax.text(0.5, 0.7, dt.datetime.utcnow().strftime('%H:%M:%S'),
        horizontalalignment='center',
        verticalalignment='center',
        fontsize=100, color='red',
        transform=ax.transAxes)

    ax.text(0.5, 0.3, dt.datetime.utcnow().strftime('%Y.%m.%d'),
        horizontalalignment='center',
        verticalalignment='center',
        fontsize=80, color='red',
        transform=ax.transAxes)

    ax.spines['top'].set_color('none')
    ax.spines['right'].set_color('none')
    ax.spines['left'].set_color('none')
    ax.xaxis.set_ticks_position('bottom')
    ax.patch.set_facecolor('black')

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=dpi, transparent=False, frameon=False, facecolor='black', edgecolor='none')
    buf.seek(0)
    plt.close(fig)

    return (skimage.io.imread(buf)[:,:,0:3]).astype('uint8')

def smart_fact2img(rows, cols):
    
    dpi = 96
    fig = plt.figure(figsize=(cols/dpi, rows/dpi), dpi=dpi)
    ax = plt.gca()
    ax.yaxis.set_visible(False)

    out =(
        'SQM\n'
        ' Magnitude.... {Magnitude:.1f}\n'
        'SIPM\n'
        ' power........ {power:.1f} {power_unit:s} \n'
        ' min med max.. {min_cur:.1f}, {med_cur:.1f}, {max_cur:.1f} {cur_unit:s}\n'
        'Temp\n'
        ' outside...... {out_temp:.1f} C\n'
        ' container.... {cont_temp:.1f} C\n'
        ' camera....... {cam_temp:.1f} C\n'
        'Source\n'
        ' name......... {source_name}\n'
        ' Azimuth...... {source_az:.1f} {source_az_unit:s}\n'
        ' Zenith....... {source_zd:.1f} {source_zd_unit:s}\n'
    ).format(
        Magnitude=sfc.sqm().magnitude.value,
        power=sfc.sipm_currents().power.value,
        power_unit=sfc.sipm_currents().power.unit,
        min_cur=sfc.sipm_currents().min_per_sipm.value,
        med_cur=sfc.sipm_currents().median_per_sipm.value,
        max_cur=sfc.sipm_currents().max_per_sipm.value,
        cur_unit=sfc.sipm_currents().max_per_sipm.unit,
        out_temp=sfc.weather().temperature.value,
        cont_temp=float(sfc.container_temperature().current.value),
        cam_temp=sfc.camera_climate().relative_temperature_mean.value + sfc.weather().temperature.value,
        source_name=sfc.current_source().name,
        source_az=sfc.drive()['pointing'].azimuth.value,
        source_zd=sfc.drive()['pointing'].zenith_distance.value,
        source_az_unit=sfc.drive()['pointing'].azimuth.unit,
        source_zd_unit=sfc.drive()['pointing'].zenith_distance.unit,
    )

    font = FontProperties()
    font.set_family('monospace')
    ax.text(0, 0.5, out,
        verticalalignment='center',
        fontsize=20, color='red',
        horizontalalignment='left',
        fontproperties=font,
        transform=ax.transAxes)

    ax.spines['top'].set_color('none')
    ax.spines['right'].set_color('none')
    ax.spines['left'].set_color('none')
    ax.xaxis.set_ticks_position('bottom')
    ax.patch.set_facecolor('black')

    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=dpi, transparent=False, frameon=False, facecolor='black', edgecolor='none')
    buf.seek(0)
    plt.close(fig)
    
    return (skimage.io.imread(buf)[:,:,0:3]).astype('uint8')   

def stack_image_list_into_rows_and_cols(imgs, big_rows, big_cols):

    rows = imgs[0].shape[0]
    cols = imgs[0].shape[1]

    col_stack = np.zeros(shape=(0,big_cols*cols,3)).astype('uint8')

    for row in range(big_rows):
            
        row_stack = np.zeros(shape=(rows,0,3)).astype('uint8')

        for col in range(big_cols):
            i = col + big_cols*row

            if i < len(imgs):
                row_stack = np.hstack((row_stack, imgs[i]))
            else:
                row_stack = np.hstack((row_stack, empty_image(rows, cols)))

        col_stack = np.vstack((col_stack, row_stack))

    return col_stack

def download_and_resize_image_to_rows_and_cols(url, rows, cols):
    req = requests.get(url, verify=False, timeout=15)
    img = skimage.io.imread(io.BytesIO(req.content), format='jpg')
    img = skimage.transform.resize(img, (rows, cols, 3))
    img = 255.0*img
    img = img.astype('uint8') 
    return img

def Vprint(verbose, text):
    if verbose:
        print(text)

def save_image(output_path, overview_config=None, verbose=False):
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
                #'http://www.gtc.iac.es/multimedia/netcam/camaraExt.jpg',
                'http://www.magic.iac.es/site/weather/lastHUM6t.jpg',
                'http://www.magic.iac.es/site/weather/lastWPK6t.jpg'
            ]
        }

    #-----------------------------------
    # the single image tiles of the stacked image are collected here
    imgs = []

    #-----------------------------------
    # Collect all the images listed in the urls
    for url in cfg['image_urls']:
        try:
            imgs.append(
                download_and_resize_image_to_rows_and_cols(
                    url, 
                    cfg['img']['rows'], 
                    cfg['img']['cols']
                )
            ) 
        except:
            imgs.append(empty_image(cfg['img']['rows'], cfg['img']['cols']))
        Vprint(verbose, url)

    #-----------------------------------
    # Append a Smart FACT status image
    try:
        imgs.append(smart_fact2img(cfg['img']['rows'], cfg['img']['cols']))
        Vprint(verbose, 'smart fact')
    except:
        imgs.append(empty_image(cfg['img']['rows'], cfg['img']['cols']))

    #-----------------------------------
    # Append a time stamp image
    try:
        imgs.append(clock2img(cfg['img']['rows'], cfg['img']['cols']))
        Vprint(verbose, 'clock')
    except:
        imgs.append(empty_image(cfg['img']['rows'], cfg['img']['cols']))

    #-----------------------------------
    # create stacked image from list of single images
    image_stack = stack_image_list_into_rows_and_cols(
        imgs, 
        cfg['stacked_image']['rows'], 
        cfg['stacked_image']['cols']
    )

    #-----------------------------------
    # save the stacked image
    skimage.io.imsave(output_path, image_stack)

def main():
    try:
        arguments = docopt.docopt(__doc__)
        save_image(
            output_path=arguments['--output'], 
            verbose=arguments['--verbose']
        )

    except docopt.DocoptExit as e:
        print(e)

if __name__ == "__main__":
    main()