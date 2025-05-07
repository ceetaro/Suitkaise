# -------------------------------------------------------------------------------------
# Copyright 2025 Casey Eddings
# Copyright (C) 2025 Casey Eddings
#
# This file is a part of the Suitkaise application, available under either
# the Apache License, Version 2.0 or the GNU General Public License v3.
#
# ~~ Apache License, Version 2.0 (http://www.apache.org/licenses/LICENSE-2.0)
#
#       Licensed under the Apache License, Version 2.0 (the "License");
#       you may not use this file except in compliance with the License.
#       You may obtain a copy of the License at
#
#           http://www.apache.org/licenses/LICENSE-2.0
#
#       Unless required by applicable law or agreed to in writing, software
#       distributed under the License is distributed on an "AS IS" BASIS,
#       WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#       See the License for the specific language governing permissions and
#       limitations under the License.
#
# ~~ GNU General Public License, Version 3 (http://www.gnu.org/licenses/gpl-3.0.html)
#
#       This program is free software: you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation, either version 3 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
# -------------------------------------------------------------------------------------

# suitkaise/eventsys/keyreg/compress_keys.py

"""
Module for compressing keys in the event system.

This module provides functionality to compress event data to reduce memory usage
and optimize transmission between components. It offers several compression strategies:

1. Standard compression algorithms (zlib, gzip, lzma)
2. Function replacement (replacing data with functions that regenerate it when needed)
3. Specialized type-specific compression

The module works with the keyreg system to determine which keys can be compressed
and how they should be compressed based on their registered properties.

"""

import zlib
import gzip
import lzma
import pickle
import base64
import importlib
import inspect
from enum import Enum, auto
from functools import partial
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, Set

import suitkaise.time.sktime as sktime
from suitkaise.eventsys.data.enums.enums import CompressionLevel
import suitkaise.eventsys.keyreg.keyreg as keyreg
import suitkaise.utils.math.byte_conversions as byteconv
import suitkaise.utils.formatting.format_data as fmt
from suitkaise.utils.fib.fib import FunctionInstance, FunctionInstanceBuilder

class CompressStrat(Enum):
    """
    Enum for different compression strategies.
    """
    NONE = auto() # No compression
    ZLIB = auto() # zlib compression (balanced)
    GZIP = auto() # gzip compression (good for text)
    LZMA = auto() # lzma compression (high compression ratio, slower)
    FUNCTION = auto() # Function replacement (regenerate data using a function)
    REMOVE = auto() # Remove the key entirely (for optional keys)
    SPECIALIZED = auto() # Specialized compression (type-specific)

class CompressedData:
    """
    Container for compressed data.

    This class holds the compressed data and its metadata, including the
    compression strategy used, the original data type, and any additional
    information needed to decompress the data.
    
    """
    def __init__(self,
                 data: bytes,
                 strategy: CompressStrat,
                 original_type: type,
                 compression_time: float,
                 original_size: int,
                 compressed_size: int):
        """
        Initialize the CompressedData container.

        Args:
            data (bytes): The compressed data.
            strategy (CompressStrat): The compression strategy used.
            original_type (type): The original type of the data.
            compression_time (float): Time taken to compress the data.
            original_size (int): Size of the original data.
            compressed_size (int): Size of the compressed data.
        
        """
        self.data = data
        self.strategy = strategy
        self.original_type = original_type
        self.compression_time = compression_time
        self.original_size = original_size
        self.compressed_size = compressed_size
        self.compression_ratio = original_size / compressed_size if compressed_size > 0 else 0

    def __repr__(self):
        """String representation of compressed data."""
        return (f"CompressedData(strategy={self.strategy.name}, "
                f"original_type={self.original_type.__name__}, "
                f"compressed_size={byteconv.convert_bytes(self.compressed_size, rounding=0)}, "
                f"ratio={self.compression_ratio:.2f}x\n")
    

def compress(key: str,
             data: Any,
             level: CompressionLevel = CompressionLevel.NORMAL
             ) -> Union[CompressedData, FunctionInstance]:
    """
    Compress data using the appropriate strategy, based on data type and compression
    level.

    Args:
        data (Any): The data to compress.
        level (CompressionLevel): The compression level to use.
        key: key associated with this data (if available)

    Returns:
        either a CompressedData object or a FunctionInstance object,
        containing the compressed data/metadata or the function to regenerate the data.
    
    """
    # determine best compression strategy based on data type and compression level
    strategy = select_compression_strategy(data, level, key)

    if strategy == CompressStrat.FUNCTION and key:
        replacement_func = keyreg.get_replacement_function(key)
        if replacement_func and isinstance(replacement_func, FunctionInstance):
            return replacement_func


    # if strategy is REMOVE
    if strategy == CompressStrat.REMOVE:
        # return None to indicate removal
        return None

    # get original size of data
    orginal_size = get_data_size(data)

    # start timer
    start_time = sktime.now()

    # compress the data based on selected strategy
    if strategy == CompressStrat.NONE:
        # still serialize the data
        compressed = pickle.dumps(data)
    elif strategy == CompressStrat.ZLIB:
        compressed = zlib.compress(pickle.dumps(data), level=get_zlib_level(level))
    elif strategy == CompressStrat.GZIP:
        compressed = gzip.compress(pickle.dumps(data), compresslevel=get_gzip_level(level))
    elif strategy == CompressStrat.LZMA:
        compressed = lzma.compress(pickle.dumps(data), preset=get_lzma_level(level))
    elif strategy == CompressStrat.SPECIALIZED:
        compressed = specialized_compression(data, level)
    else:
        raise ValueError(f"Unknown compression strategy: {strategy}")
    
    # end timer
    end_time = sktime.now()

    # create and return compressed data container
    return CompressedData(
        data=compressed,
        strategy=strategy,
        original_type=type(data),
        compression_time=end_time - start_time,
        original_size=orginal_size,
        compressed_size=len(compressed)
    )


def decompress(compressed_data: Union[CompressedData, FunctionInstance]) -> Any:
    """
    Decompress data that was previously compressed.

    Args:
        compressed_data: The compressed data, which is either a CompressedData container
        or a FunctionReplacement object.

    Returns:
        The decompressed data.

    """
    # extract the strategy and compressed data from the container
    if isinstance(compressed_data, CompressedData):
        strategy = compressed_data.strategy
        compressed = compressed_data.data
    elif isinstance(compressed_data, FunctionInstance):
        # execute the function to regenerate the data
        return compressed_data.execute()
    else:
        raise ValueError("Invalid compressed data type")
    
    if strategy == CompressStrat.NONE:
        # still serialize the data
        return pickle.loads(compressed)
    elif strategy == CompressStrat.ZLIB:
        return pickle.loads(zlib.decompress(compressed))
    elif strategy == CompressStrat.GZIP:
        return pickle.loads(gzip.decompress(compressed))
    elif strategy == CompressStrat.LZMA:
        return pickle.loads(lzma.decompress(compressed))
    elif strategy == CompressStrat.SPECIALIZED:
        return specialized_decompression(compressed, compressed_data.original_type)
    else:
        raise ValueError(f"Unsupported compression strategy: {strategy}")
    

def select_compression_strategy(data: Any, 
                                level: CompressionLevel,
                                key: str = None) -> CompressStrat:
    """
    Select the best compression strategy to use on this data.

    Args:
        data (Any): The data to compress.
        level (CompressionLevel): The compression level to use.
        key (str): The key associated with this data (if available).

    Returns:
        CompressStrat: The selected compression strategy.
    
    """
    if has_specialized_compression(data):
        return CompressStrat.SPECIALIZED

    # check if a replacement function is available for this key
    if keyreg.is_registered(key) and keyreg.has_replacement_function(key):
        return CompressStrat.FUNCTION
    
    # simple types that don't need compression
    if isinstance(data, (int, float, bool, complex, type(None))):
        return CompressStrat.NONE
    
    # small strings and bytes that don't need compression
    if isinstance(data, (str, bytes)) and len(data) <= 100:
        return CompressStrat.NONE
    
    # text-heavy, use gzip
    if isinstance(data, str) and len(data) > 100:
        return CompressStrat.GZIP
    
    # check for optional keys at high level
    if key and level == CompressionLevel.HIGH and keyreg.is_optional(key):
        return CompressStrat.REMOVE
    
    # binary data, use zlib
    if level == CompressionLevel.NORMAL or level == CompressionLevel.LOW:
        return CompressStrat.ZLIB
    # high compression, use lzma
    elif level == CompressionLevel.HIGH:
        return CompressStrat.LZMA
    

    
    print(f"No conditions met, using strategy CompressStrat.NONE")
    return CompressStrat.NONE


def get_data_size(data: Any) -> int:
    """
    Get the size of the data in bytes.

    Args:
        data (Any): The data to get the size of.

    Returns:
        int: The size of the data in bytes.
    
    """
    try:
        return len(pickle.dumps(data))
    except Exception as e:
        print(f"Error getting data size: {e}")
        return 0
    
def get_zlib_level(level: CompressionLevel) -> int:
    """
    Get the zlib compression level based on the CompressionLevel enum.

    Args:
        level (CompressionLevel): The compression level to convert.

    Returns:
        int: The zlib compression level.
    
    """
    if level == CompressionLevel.LOW:
        zlib_level = 3
    elif level == CompressionLevel.NORMAL:
        zlib_level = 6
    elif level == CompressionLevel.HIGH:
        zlib_level = 9
    else:
        raise ValueError(f"Invalid compression level: {level}")
    
    print(f"Zlib compression level: {zlib_level}")
    return zlib_level

def get_gzip_level(level: CompressionLevel) -> int:
    """
    Get the gzip compression level based on the CompressionLevel enum.

    Args:
        level (CompressionLevel): The compression level to convert.

    Returns:
        int: The gzip compression level.
    
    """
    return get_zlib_level(level)

def get_lzma_level(level: CompressionLevel) -> int:
    """
    Get the lzma compression level based on the CompressionLevel enum.

    Args:
        level (CompressionLevel): The compression level to convert.

    Returns:
        int: The lzma compression level.
    
    """
    if level == CompressionLevel.LOW:
        lzma_level = 1
    elif level == CompressionLevel.NORMAL:
        lzma_level = 5
    elif level == CompressionLevel.HIGH:
        lzma_level = 9
    else:
        raise ValueError(f"Invalid compression level: {level}")
    
    print(f"LZMA compression level: {lzma_level}")
    return lzma_level

def has_specialized_compression(data: Any) -> bool:
    """
    Check if the data has specialized compression available.

    Args:
        data (Any): The data to check.

    Returns:
        bool: True if specialized compression is available, False otherwise.
    
    """
    # implement specialized compression check logic here
    # For now, we will just return False to indicate no specialized compression
    return False

def specialized_compression(data: Any, level: CompressionLevel) -> bytes:
    """
    Perform specialized compression on the data.

    Args:
        data (Any): The data to compress.
        level (CompressionLevel): The compression level to use.

    Returns:
        bytes: The compressed data.
    
    """
    # implement specialized compression logic here
    # For now, we will just return the original data as is
    print(f"Specialized compression not implemented, just pickling data\n")
    return pickle.dumps(data)

def specialized_decompression(data: bytes, original_type: type) -> Any:
    """
    Perform specialized decompression on the data.

    Args:
        data (bytes): The compressed data to decompress.
        original_type (type): The original type of the data.

    Returns:
        Any: The decompressed data.
    
    """
    # implement specialized decompression logic here
    # For now, we will just return the original data as is
    print(f"Specialized decompression not implemented, just unpickling data\n")
    return pickle.loads(data)
        

    
    



        
    

    


