# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

{
  'variables': {
    'conditions': [
      ['OS == "android" or OS == "ios"', {
        # Android and iOS don't use ffmpeg.
        'use_ffmpeg%': 0,
      }, {  # 'OS != "android" and OS != "ios"'
        'use_ffmpeg%': 1,
      }],
    ],
    # Set |use_fake_video_decoder| to 1 to ignore input frames in |clearkeycdm|,
    # and produce video frames filled with a solid color instead.
    'use_fake_video_decoder%': 0,
    # Set |use_libvpx| to 1 to use libvpx for VP8 decoding in |clearkeycdm|.
    'use_libvpx%': 0,
  },
  'targets': [
    {
      'target_name': 'webkit_media',
      'type': 'static_library',
      'variables': { 'enable_wexit_time_destructors': 1, },
      'dependencies': [
        '<(DEPTH)/base/base.gyp:base',
        '<(DEPTH)/base/third_party/dynamic_annotations/dynamic_annotations.gyp:dynamic_annotations',
        '<(DEPTH)/cc/cc.gyp:cc',
        '<(DEPTH)/media/media.gyp:media',
        '<(DEPTH)/media/media.gyp:shared_memory_support',
        '<(DEPTH)/skia/skia.gyp:skia',
        '<(DEPTH)/third_party/WebKit/public/blink.gyp:blink',
        '<(DEPTH)/webkit/renderer/compositor_bindings/compositor_bindings.gyp:webkit_compositor_bindings',
      ],
      'sources': [
        'crypto/ppapi_decryptor.cc',
        'crypto/ppapi_decryptor.h',
      ],
      'conditions': [
        ['OS == "android"', {
          'dependencies': [
            '<(DEPTH)/media/media.gyp:player_android',
          ],
        }, { # OS != "android"'
          'sources/': [
            ['exclude', '^android/'],
          ],
        }],
        ['enable_pepper_cdms != 1', {
          'sources!': [
            'crypto/ppapi_decryptor.cc',
            'crypto/ppapi_decryptor.h',
          ],
        }],
      ],
      # TODO(jschuh): crbug.com/167187 fix size_t to int truncations.
      'msvs_disabled_warnings': [ 4267, ],
    },
    {
      'target_name': 'clearkeycdm',
      'type': 'none',
      # TODO(tomfinegan): Simplify this by unconditionally including all the
      # decoders, and changing clearkeycdm to select which decoder to use
      # based on environment variables.
      'conditions': [
        ['use_fake_video_decoder == 1' , {
          'defines': ['CLEAR_KEY_CDM_USE_FAKE_VIDEO_DECODER'],
          'sources': [
            'crypto/ppapi/fake_cdm_video_decoder.cc',
            'crypto/ppapi/fake_cdm_video_decoder.h',
          ],
        }],
        ['use_ffmpeg == 1'  , {
          'defines': ['CLEAR_KEY_CDM_USE_FFMPEG_DECODER'],
          'dependencies': [
            '<(DEPTH)/third_party/ffmpeg/ffmpeg.gyp:ffmpeg',
          ],
          'sources': [
            'crypto/ppapi/ffmpeg_cdm_audio_decoder.cc',
            'crypto/ppapi/ffmpeg_cdm_audio_decoder.h',
          ],
        }],
        ['use_ffmpeg == 1 and use_fake_video_decoder == 0'  , {
          'sources': [
            'crypto/ppapi/ffmpeg_cdm_video_decoder.cc',
            'crypto/ppapi/ffmpeg_cdm_video_decoder.h',
          ],
        }],
        ['use_libvpx == 1 and use_fake_video_decoder == 0' , {
          'defines': ['CLEAR_KEY_CDM_USE_LIBVPX_DECODER'],
          'dependencies': [
            '<(DEPTH)/third_party/libvpx/libvpx.gyp:libvpx',
          ],
          'sources': [
            'crypto/ppapi/libvpx_cdm_video_decoder.cc',
            'crypto/ppapi/libvpx_cdm_video_decoder.h',
          ],
        }],
        ['os_posix == 1 and OS != "mac" and enable_pepper_cdms==1', {
          'type': 'loadable_module',  # Must be in PRODUCT_DIR for ASAN bots.
        }],
        ['(OS == "mac" or OS == "win") and enable_pepper_cdms==1', {
          'type': 'shared_library',
        }],
        ['OS == "mac"', {
          'xcode_settings': {
            'DYLIB_INSTALL_NAME_BASE': '@loader_path',
          },
        }]
      ],
      'defines': ['CDM_IMPLEMENTATION'],
      'dependencies': [
        '<(DEPTH)/base/base.gyp:base',
        '<(DEPTH)/media/media.gyp:media',
        # Include the following for media::AudioBus.
        '<(DEPTH)/media/media.gyp:shared_memory_support',
      ],
      'sources': [
        'crypto/ppapi/cdm_video_decoder.cc',
        'crypto/ppapi/cdm_video_decoder.h',
        'crypto/ppapi/clear_key_cdm.cc',
        'crypto/ppapi/clear_key_cdm.h',
      ],
      # TODO(jschuh): crbug.com/167187 fix size_t to int truncations.
      'msvs_disabled_warnings': [ 4267, ],
    },
    {
      'target_name': 'clearkeycdmadapter',
      'type': 'none',
      # Check whether the plugin's origin URL is valid.
      'defines': ['CHECK_DOCUMENT_URL'],
      'dependencies': [
        '<(DEPTH)/ppapi/ppapi.gyp:ppapi_cpp',
        'clearkeycdm',
      ],
      'sources': [
        'crypto/ppapi/cdm_wrapper.cc',
        'crypto/ppapi/cdm/content_decryption_module.h',
        'crypto/ppapi/linked_ptr.h',
      ],
      'conditions': [
        ['os_posix == 1 and OS != "mac" and enable_pepper_cdms==1', {
          'cflags': ['-fvisibility=hidden'],
          'type': 'loadable_module',
          # Allow the plugin wrapper to find the CDM in the same directory.
          'ldflags': ['-Wl,-rpath=\$$ORIGIN'],
          'libraries': [
            # Built by clearkeycdm.
            '<(PRODUCT_DIR)/libclearkeycdm.so',
          ],
        }],
        ['OS == "win" and enable_pepper_cdms==1', {
          'type': 'shared_library',
          # TODO(jschuh): crbug.com/167187 fix size_t to int truncations.
          'msvs_disabled_warnings': [ 4267, ],
        }],
        ['OS == "mac" and enable_pepper_cdms==1', {
          'type': 'loadable_module',
          'product_extension': 'plugin',
          'xcode_settings': {
            'OTHER_LDFLAGS': [
              # Not to strip important symbols by -Wl,-dead_strip.
              '-Wl,-exported_symbol,_PPP_GetInterface',
              '-Wl,-exported_symbol,_PPP_InitializeModule',
              '-Wl,-exported_symbol,_PPP_ShutdownModule'
            ],
            'DYLIB_INSTALL_NAME_BASE': '@loader_path',
          },
        }],
      ],
    }
  ],
}