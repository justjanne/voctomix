#!/usr/bin/env python3
import logging
import gi
import sys

from gi.repository import Gst

gi.require_version('GstController', '1.0')

from vocto.config import VocConfigParser

log = logging.getLogger('video_codecs')

vaapi_encoders = {
    'h264': 'vapostproc ! vah264enc key-int-max=1',
    'h265': 'vapostproc ! vah265enc key-int-max=1',
    'jpeg': 'vapostproc ! vajpegenc',
}

v4l2_encoders = {
    'h264': 'v4l2h264enc',
    'jpeg': 'v4l2jpegenc',
}

cpu_encoders = {
    'jpeg': "jpegenc",
    'h264': "x264enc",
    'mpeg2': "mpeg2enc"
}

vaapi_decoders = {
    'h264': 'h264parse ! vah264dec ! vapostproc',
    'h265': 'h265parse ! vah265dec ! vapostproc',
    'jpeg': 'vajpegdec ! vapostproc',
}

cpu_decoders = {
    'h264': """ video/x-h264
                ! h264parse ! avdec_h264""",
    'jpeg': """ image/jpeg
                ! jpegdec""",
    'mpeg2': """video/mpeg
                    mpegversion=2
                ! mpeg2dec"""
}


def construct_video_encoder_pipeline(config: VocConfigParser, section: str) -> str:
    encoder = config.getVideoEncoder(section)
    codec, options = config.getVideoCodec(section)
    vcaps = config.getVideoCaps(section)

    pipeline = ""

    if encoder == 'vaapi':
        encoder = config.getVaCoreElement(codec) or vaapi_encoders[codec]
        if not encoder:
            log.error("Unknown codec '{}' for video encoder '{}'.".format(codec, encoder))
            sys.exit(-1)
        # generate pipeline
        # we can also force a video format here (format=I420) but this breaks scalling at least on Intel HD3000 therefore it currently removed
        pipeline = """  ! capsfilter
                            caps=video/x-raw,interlace-mode=progressive
                        ! {encoder}
                        """.format(encoder=encoder)

    elif encoder == 'v4l2':
        if codec not in v4l2_encoders:
            log.error("Unknown codec '{}' for video encoder '{}'.".format(codec, encoder))
            sys.exit(-1)
        pipeline = """  ! capsfilter
                            caps=video/x-raw,interlace-mode=progressive
                        ! {encoder}
                        """.format(encoder=v4l2_encoders[codec])

    elif encoder == "cpu":
        if codec not in cpu_encoders:
            log.error("Unknown codec '{}' for video encoder '{}'.".format(codec, encoder))
            sys.exit(-1)
        # maybe add deinterlacer
        if config.getDeinterlace(section):
            pipeline += """ ! deinterlace
                                mode=interlaced
                        """
        # build rest of the pipeline
        pipeline += """ ! videorate
                        ! videoscale
                        ! {encoder}
                        """.format(encoder=cpu_encoders[codec])
    else:
        log.error("Unknown video encoder '{}'.".format(encoder))
        sys.exit(-1)

    if options:
        pipeline += """{options}
                        """.format(options='\n'.join(options))

    pipeline += """! {vcaps}
                """.format(vcaps=vcaps)

    if codec.startswith("h264"):
        pipeline += """! h264parse"""
    elif codec.startswith("h265"):
        pipeline += """! h265parse"""

    return pipeline


def construct_video_decoder_pipeline(config: VocConfigParser, section: str) -> str:
    decoder = config.getVideoDecoder(section)
    codec, options = config.getVideoCodec(section)
    if decoder == 'vaapi':
        return config.getVaClientElement(codec) or vaapi_decoders[codec]
    elif decoder == 'cpu':
        return cpu_decoders[codec]
    else:
        log.error("Unknown video decoder '{}'.".format(decoder))
        exit(-1)
