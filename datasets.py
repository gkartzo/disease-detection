from abc import ABCMeta, abstractmethod, abstractproperty
import os
import numpy as np
import pandas as pd
from PIL import Image
import skimage.transform
from lasagne.utils import floatX


class Dataset(object):
    """Base class for actual datasets"""

    __metaclass__ = ABCMeta

    @abstractproperty
    def n_samples(self):
        pass

    @abstractmethod
    def load_batch(self, indices):
        """
        Load a batch of data samples together with labels

        Parameters
        ----------
        indices: array-like, shape = (n_samples,)
            with respect to the entire data set

        Returns
        -------
        X : numpy array, shape = (n_samples, n_channels, n_rows, n_columns)
            batch of data
        y : numpy array, shape = (n_samples,)

        """

    def iterate_minibatches(self, indices, batchsize, shuffle=False):
        """
        Generator that yields a batch of data together with labels

        Parameters
        ----------
        indices : array-like, shape = (n_samples,)
            with respect to the entire data set
        batch_size : int
        shuffle : boolean (False by default)
            shuffle indices

        Returns
        -------
        X : numpy array, shape = (n_samples, n_channels, n_rows, n_columns)
            batch of data
        y : numpy array, shape = (n_samples,)

        Notes
        -----
        Currently len(indices)%batch_size samples are not used!

        """

        if shuffle:
            np.random.shuffle(indices)
        for start_idx in range(0, len(indices) - batch_size + 1, batch_size):
            excerpt = indices[start_idx:start_idx + batch_size]
            yield self.load_batch(excerpt)


class KaggleDR(Dataset):
    """
    Provides access to data from Kaggle's Diabetic Retinopathy competition.

    """

    def __init__(self, path_data=None, filename_targets=None):
        self.path_data = path_data
        self.filename_targets = filename_targets
        labels = pd.read_csv(self.filename_targets)
        self.image_filenames = labels['image']
        self.y = np.array(labels['level'])
        self._n_samples = len(self.y)

    @property
    def n_samples(self):
        """Number of samples in the entire dataset"""
        return self._n_samples

    def load_image(self, filename):
        """
        Load image.

        Parameters
        ----------
        filename : string
            relative filename (path to image folder gets prefixed)

        Returns
        -------
        image : numpy array, shape = (n_rows, n_columns, n_channels)

        """

        filename = os.path.join(self.path_data, filename + '.jpeg')
        return np.array(Image.open(filename))

    @staticmethod
    def prep_image(im):
        """
        Preprocess image.

        Resizes smaller spatial extent to 256 pixels while preserving the
        aspect ratio. Central part of image is cropped to 224 x 224.
        No mean subtraction. Colour channels are inverted: RGB -> BGR
        Dimensions get reordered.

        Parameters
        ----------
        im : numpy array, shape = (n_rows, n_columns, n_channels)

        Returns
        -------
        processed image : numpy array, shape = (n_channels, n_rows, n_columns)
                                       dtype = floatX

        """

        # Resize so smallest dim = 256, preserving aspect ratio
        h, w, _ = im.shape
        if h < w:
            im = skimage.transform.resize(im, (256, w*256/h),
                                          preserve_range=True)
        else:
            im = skimage.transform.resize(im, (h*256/w, 256),
                                          preserve_range=True)
        # Central crop to 224x224
        h, w, _ = im.shape
        im = im[h//2-112:h//2+112, w//2-112:w//2+112]
        # Returned image should be (n_channels, n_rows, n_columns)
        im = np.transpose(im, (2, 0, 1))
        # Convert to BGR
        im = im[::-1, :, :]
        return floatX(im)

    def load_batch(self, indices):
        """
        Load batch of preprocessed data samples together with labels

        Parameters
        ----------

        indices : array_like, shape = (batch_size,)
            absolute index values refer to position in trainLabels.csv

        """

        X = np.array([self.prep_image(self.load_image(fn)) for fn in
                      self.image_filenames[indices]])
        y = self.y[indices]
        assert len(X) == len(y) == len(indices)
        return X, y

