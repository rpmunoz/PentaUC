import numpy as np
import matplotlib.pyplot as plt

from astropy import units as u
from astropy.io import fits
from astropy.coordinates import SkyCoord, Angle
from astropy.nddata import Cutout2D
from astropy.wcs import WCS
from astroquery.sdss import SDSS

import requests, StringIO, urllib
from PIL import Image

from astroML.plotting import setup_text_plots
setup_text_plots(usetex=True,fontsize=18)

absorption_lines={'name':['CaII K','CaII H','Mgb'], 'lambda':[3933.,3968,5183.], 'align':['right','left','left'], 'offset':[-50,50,50]}

def imtoasinh(im_data):
    asinh_percentile=[0.25,99.5]
    asinh_midpoint=-0.07

    im_gray=im_data.copy()
    im_gray = np.nan_to_num(im_gray)
    im_gray_percentile=np.percentile(im_gray,asinh_percentile)
    im_gray_min=im_gray_percentile[0]
    im_gray_max=im_gray_percentile[1]

    print "FITS image - min=%.2f  max=%.2f" % (im_gray_min, im_gray_max)

    im_gray=(im_gray-im_gray_min)/(im_gray_max-im_gray_min)
    im_gray=np.arcsinh(im_gray/asinh_midpoint)/np.arcsinh(1./asinh_midpoint)
    im_gray = np.nan_to_num(im_gray)
    im_gray = np.clip(im_gray, 0., 1.)
    
    return im_gray

def sdss_jpg(coo):
    
    try:
        n_coo=len(coo)
    except:
        n_coo=1
        coo=[coo]
        
    impix = 320
    imsize = 1*u.arcmin
    cutoutbaseurl = 'http://skyservice.pha.jhu.edu/DR12/ImgCutout/getjpeg.aspx'

    fig, ax = plt.subplots(figsize=(30,30), sharex=True, sharey=True)
    for i in range(len(coo)):
        ax = plt.subplot(np.floor(np.sqrt(n_coo)),np.ceil(np.sqrt(n_coo)),i+1)
        print 'Procesando galaxia '+str(i+1)
        query_string = urllib.urlencode(dict(ra=coo[i].ra.deg, 
                                         dec=coo[i].dec.deg, 
                                         width=impix, height=impix, 
                                         scale=imsize.to(u.arcsec).value/impix))
        url = cutoutbaseurl + '?' + query_string

        r = requests.get(url)
        im_data=Image.open(StringIO.StringIO(r.content))
        
        ax.imshow(im_data)
        ax.axis('off')
        ax.text(0.05,0.05, str(i+1), transform=ax.transAxes, color='white', fontsize=14)
        
    fig.subplots_adjust(hspace=0.1, wspace=0.1)

def sdss_fits(coo):
    
    try:
        n_coo=len(coo)
    except:
        n_coo=1
        coo=[coo]

    fig, ax = plt.subplots(figsize=(30,30), sharex=True, sharey=True)
    for i in range(len(coo)):
        ax = plt.subplot(np.floor(np.sqrt(n_coo)), np.ceil(np.sqrt(n_coo)),i+1)
        print 'Procesando galaxia '+str(i+1)
        xid = SDSS.query_region(coo[i], spectro=True)
        image=SDSS.get_images(matches=xid)[0][0]

        im_h=image.header
        im_data=image.data

        im_median=np.median(im_data)
        im_std=np.std(im_data)

        im_wcs = WCS(im_h)
        im_data = Cutout2D(im_data, coo[i], u.Quantity((1., 1.), u.arcmin), wcs=im_wcs).data

#        ax.imshow(im_data,vmin=im_median-1*im_std, vmax=im_median+5*im_std, cmap=plt.get_cmap('gray'), interpolation='nearest')
        ax.imshow(imtoasinh(im_data.T), vmin=0.1, vmax=0.8, cmap=plt.get_cmap('gray'), interpolation='nearest', origin='lower')
        ax.axis('off')
        ax.text(0.05,0.05, str(i+1), transform=ax.transAxes, color='white', fontsize=14)
        ax.invert_xaxis()
        
    fig.subplots_adjust(hspace=0.1, wspace=0.1)
    
def sdss_spectra(coo, redshift=0.):
    
    try:
        n_coo=len(coo)
    except:
        n_coo=1
        coo=[coo]

    try:
        n_redshift=len(redshift)
    except:
        n_redshift=1
        redshift=[redshift]


    if n_coo>1 & n_redshift==1:
      redshift=np.ones(n_coo)*redshift[0]

    fig, ax = plt.subplots(figsize=(30,10*n_coo), sharex=True, sharey=True)
    for i in range(len(coo)):
        ax = plt.subplot(n_coo, 1,i+1)
        print 'Procesando galaxia '+str(i+1)
        xid = SDSS.query_region(coo[i], spectro=True)
        spec=SDSS.get_spectra(matches=xid)[0][1]

        spec_h=spec.header
        spec_data=spec.data

        loglam=spec_data['loglam']
        flux=np.convolve(spec_data['flux'],np.ones((10,))/10, mode='same')

        ax.plot(10.**loglam/(1.+redshift[i]), flux, label=xid['instrument'][0])
        for j in range(len(absorption_lines['name'])):
          ax.plot(absorption_lines['lambda'][j]*np.ones(2), [0., 1e5], 'r--') 
          ax.text(absorption_lines['lambda'][j]+absorption_lines['offset'][j], 5., absorption_lines['name'][j], color='black', fontsize=16, horizontalalignment=absorption_lines['align'][j])

        ax.set_ylabel('Flujo [10$^{-17}$ ergs/cm$^2$/s/\AA]')
        ax.set_xlabel('Longitud de onda [\AA]')
        ax.set_title('Galaxia '+str(i+1))
        ax.set_xlim(3500,9000)
        ax.set_ylim(0.,100.)
        
    fig.subplots_adjust(hspace=0.2, wspace=0.1)


def sdss_template(tipo='eliptica'):

  if tipo=='eliptica':
    template = SDSS.get_spectral_template('galaxy_early')
    title='Espectro de galaxia eliptica'
  elif tipo=='espiral': 
    template = SDSS.get_spectral_template('galaxy_late')
    title='Espectro de galaxia espiral'

    spec_h=template[0][0].header
    spec_data=template[0][0].data
    wcs=WCS(spec_h)  

    index = np.arange(spec_h['NAXIS1'])
    loglam=wcs.wcs_pix2world(index, np.zeros(len(index)), 0)[0]
    flux=spec_data[0]/np.max(spec_data[0])*80.
  
    fig, ax = plt.subplots(figsize=(30,10), sharex=True, sharey=True)
    plt.plot(10**loglam, flux, '-')
    for j in range(len(absorption_lines['name'])):
      ax.plot(absorption_lines['lambda'][j]*np.ones(2), [0., 1e5], 'r--')
      ax.text(absorption_lines['lambda'][j]+absorption_lines['offset'][j], 5., absorption_lines['name'][j], color='black', fontsize=16, horizontalalignment=absorption_lines['align'][j])
  
    ax.set_ylabel('Flujo [10$^{-17}$ ergs/cm$^2$/s/\AA]')
    ax.set_xlabel('Longitud de onda [\AA]')
    ax.set_title(title)
    ax.set_xlim(3500,9000)
    ax.set_ylim(0.,100.)