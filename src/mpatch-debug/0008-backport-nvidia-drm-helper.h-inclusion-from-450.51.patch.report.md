# Mpatch Debug Report

> **Note:** This report has been partially anonymized. Please review for any remaining sensitive information before sharing.

- **Mpatch Version:** `1.6.4`
- **OS:** `linux`
- **Architecture:** `x86_64`
- **Timestamp (Unix):** `1790784825`

## Command Line

```sh
mpatch -vvvv --dry-run <INPUT_FILE> <TARGET_DIR>
```

## Input Patch File

````markdown
From 70a7eee4bbffa9a4efcf3124284f8e726ea893bc Mon Sep 17 00:00:00 2001
From: Andreas Beckmann <anbe@debian.org>
Date: Thu, 25 May 2023 00:11:05 +0200
Subject: [PATCH] backport nvidia-drm-helper.h inclusion from 450.51

---
 nvidia-drm/nvidia-drm-fb.c | 1 +
 1 file changed, 1 insertion(+)

diff --git a/nvidia-drm/nvidia-drm-fb.c b/nvidia-drm/nvidia-drm-fb.c
index 725164a..c35e0ee 100644
--- a/nvidia-drm/nvidia-drm-fb.c
+++ b/nvidia-drm/nvidia-drm-fb.c
@@ -29,6 +29,7 @@
 #include "nvidia-drm-fb.h"
 #include "nvidia-drm-utils.h"
 #include "nvidia-drm-gem.h"
+#include "nvidia-drm-helper.h"
 
 #include <drm/drm_crtc_helper.h>
 
-- 
2.20.1


````

## Original Target File(s)

### File: `nvidia-drm/nvidia-drm-fb.c`

````c
/*
 * Copyright (c) 2015, NVIDIA CORPORATION. All rights reserved.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
 * THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 * DEALINGS IN THE SOFTWARE.
 */

#include "nvidia-drm-conftest.h" /* NV_DRM_ATOMIC_MODESET_AVAILABLE */

#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)

#include "nvidia-drm-priv.h"
#include "nvidia-drm-ioctl.h"
#include "nvidia-drm-fb.h"
#include "nvidia-drm-utils.h"
#include "nvidia-drm-gem.h"

#include <drm/drm_crtc_helper.h>

static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)
{
    struct nv_drm_device *nv_dev = to_nv_device(fb->dev);

    struct nv_drm_framebuffer *nv_fb = to_nv_framebuffer(fb);

    /* Unreference gem object */

    nv_drm_gem_object_unreference_unlocked(&nv_fb->nv_nvkms_memory->base);

    /* Cleaup core framebuffer object */

    drm_framebuffer_cleanup(fb);

    /* Free NvKmsKapiSurface associated with this framebuffer object */

    nvKms->destroySurface(nv_dev->pDevice, nv_fb->pSurface);

    /* Free framebuffer */

    nv_drm_free(nv_fb);
}

static int
nv_drm_framebuffer_create_handle(struct drm_framebuffer *fb,
                                 struct drm_file *file, unsigned int *handle)
{
    struct nv_drm_framebuffer *nv_fb = to_nv_framebuffer(fb);

    return nv_drm_gem_handle_create(file,
                                    &nv_fb->nv_nvkms_memory->base,
                                    handle);
}

static struct drm_framebuffer_funcs nv_framebuffer_funcs = {
    .destroy       = nv_drm_framebuffer_destroy,
    .create_handle = nv_drm_framebuffer_create_handle,
};

static struct nv_drm_framebuffer *nv_drm_framebuffer_alloc(
    struct drm_device *dev,
    struct drm_file *file,
    NvU32 handle,
    NvU32 pixel_format)
{
    struct nv_drm_device *nv_dev = to_nv_device(dev);
    struct nv_drm_framebuffer *nv_fb;
    struct nv_drm_gem_nvkms_memory *nv_nvkms_memory;
    enum NvKmsSurfaceMemoryFormat format;

    /* Check whether NvKms supports the given pixel format */

    if (!drm_format_to_nvkms_format(pixel_format, &format)) {
        NV_DRM_DEV_LOG_ERR(
            nv_dev,
            "Unsupported drm pixel format 0x%08x", pixel_format);
        return ERR_PTR(-EINVAL);
    }

    if ((nv_nvkms_memory = nv_drm_gem_object_nvkms_memory_lookup(
                    dev,
                    file,
                    handle)) == NULL) {
        NV_DRM_DEV_LOG_ERR(
            nv_dev,
            "Failed to find gem object of type nvkms memory");
        return ERR_PTR(-ENOENT);
    }

    /* Allocate memory for the framebuffer object */

    nv_fb = nv_drm_calloc(1, sizeof(*nv_fb));

    if (nv_fb == NULL) {
        NV_DRM_DEV_LOG_ERR(
            nv_dev,
            "Failed to allocate memory for framebuffer obejct");
        nv_drm_gem_object_unreference_unlocked(&nv_nvkms_memory->base);
        return ERR_PTR(-ENOMEM);
    }

    nv_fb->nv_nvkms_memory = nv_nvkms_memory;

    return nv_fb;
}

static int nv_drm_framebuffer_init(
    struct drm_device *dev,
    struct nv_drm_framebuffer *nv_fb,
    NvU32 pixel_format)
{
    struct nv_drm_device *nv_dev = to_nv_device(dev);
    enum NvKmsSurfaceMemoryFormat format;
    int ret;

    NV_DRM_WARN(!drm_format_to_nvkms_format(pixel_format, &format));

    /* Initialize the base framebuffer object and add it to drm subsystem */

    ret = drm_framebuffer_init(dev, &nv_fb->base, &nv_framebuffer_funcs);

    if (ret != 0) {
        NV_DRM_DEV_LOG_ERR(nv_dev, "Failed to initialize framebuffer object");
        return ret;
    }

    /* Create NvKmsKapiSurface */

    nv_fb->pSurface = nvKms->createSurface(
        nv_dev->pDevice, nv_fb->nv_nvkms_memory->pMemory,
        format, nv_fb->base.width, nv_fb->base.height, nv_fb->base.pitches[0]);

    if (nv_fb->pSurface == NULL) {
        NV_DRM_DEV_LOG_ERR(nv_dev, "Failed to create NvKmsKapiSurface");
        drm_framebuffer_cleanup(&nv_fb->base);
        return -EINVAL;
    }

    return 0;
}

struct drm_framebuffer *nv_drm_internal_framebuffer_create(
    struct drm_device *dev,
    struct drm_file *file,
    struct drm_mode_fb_cmd2 *cmd)
{
    struct nv_drm_framebuffer *nv_fb;
    int ret;

    /*
     * In case of planar formats, this ioctl allows up to 4 buffer objects with
     * offsets and pitches per plane.
     *
     * We don't support any planar format, pick up first buffer only.
     */

    nv_fb = nv_drm_framebuffer_alloc(dev, file, cmd->handles[0],
                                     cmd->pixel_format);

    if (IS_ERR(nv_fb)) {
        return (struct drm_framebuffer *)nv_fb;
    }

    /* Fill out framebuffer metadata from the userspace fb creation request */

    drm_helper_mode_fill_fb_struct(
        #if defined(NV_DRM_HELPER_MODE_FILL_FB_STRUCT_HAS_DEV_ARG)
        dev,
        #endif
        &nv_fb->base,
        cmd);

    /*
     * Finish up FB initialization by creating the backing NVKMS surface and
     * publishing the DRM fb
     */

    ret = nv_drm_framebuffer_init(dev, nv_fb, cmd->pixel_format);

    if (ret != 0) {
        nv_drm_gem_object_unreference_unlocked(&nv_fb->nv_nvkms_memory->base);
        nv_drm_free(nv_fb);
        return ERR_PTR(ret);
    }

    return &nv_fb->base;
}

#endif

````

## Full Trace Log

````log

Found 1 patch operation(s) to perform.
Fuzzy matching enabled with threshold: 0.70
debug: apply_patches_to_dir: applying 1 patch(es) to '.' (dry_run=true, fuzz=0.70)
debug:   [1/1] Applying patch for 'nvidia-drm/nvidia-drm-fb.c' (1 hunk(s))
Applying patch to: nvidia-drm/nvidia-drm-fb.c
debug:   apply_patch_to_file: target_dir='.', hunks=1, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'nvidia-drm/nvidia-drm-fb.c'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-drm")' on virtual path '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-drm-fb.c")' on virtual path '<TARGET_DIR>/nvidia-drm'
trace:   Path safety verified: 'nvidia-drm/nvidia-drm-fb.c' safely resolves to '<TARGET_DIR>/nvidia-drm/nvidia-drm-fb.c'
debug:   Resolved safe target path: '<TARGET_DIR>/nvidia-drm/nvidia-drm-fb.c'
debug:   Target file exists: '<TARGET_DIR>/nvidia-drm/nvidia-drm-fb.c'. Reading content...
trace:     Read 6166 bytes (203 lines) from target file.
debug:   Applying patch logic to content in-memory...
debug: apply_patch_to_content: patch for 'nvidia-drm/nvidia-drm-fb.c' (1 hunks), original content: 6166 bytes
debug:   apply_patch_to_lines called with 203 lines of original content.
debug: resolve_hunk_line_hints: evaluating 1 hunk(s) across 203 target lines
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:   Hunk 1: already has explicit line hint 29
trace: resolve_hunk_line_hints: beginning relaxation pass 1
debug: resolve_hunk_line_hints: completed hint resolution. 1/1 hunk(s) have anchors.
debug: HunkApplier: initialized with 1 hunk(s) across 203 line(s) of target content (fuzz_factor=0.70, dry_run=true)
trace: HunkApplier::set_original_newline_status: original_ends_with_newline=true
debug: apply_hunk_to_lines: applying hunk with 9 line(s) against target with 203 line(s)
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:   Match block: ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "- ", "2.20.1"]
trace: Hunk::get_replace_block: extracted 8 replacement line(s)
trace:   Replace block: ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "#include \"nvidia-drm-helper.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "2.20.1"]
trace: Hunk::has_changes: true
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: Hunk::required_match_span: calculated required match span as 5 line(s) (first_match_idx=Some(2), last_match_idx=Some(6))
trace: DefaultHunkFinder::find_candidate_locations: match block len=8, required_match_span=5, target lines=203
trace:   find_hunk_location_internal: match_block has 8 lines (entropy=true), target has 203 lines
trace:   find_hunk_location_internal called for a hunk with 8 lines to match against 203 target lines.
trace:     Attempting exact match for hunk (match block has 8 line(s))...
trace: tie_break_with_line_number: strategy='exact', hint=Some(29), entropy=true
trace:       No exact matches found.
trace:     Strategy 1 (Exact): no exact match found.
trace:     Attempting exact match (ignoring trailing whitespace) for hunk (match block has 8 line(s))...
trace: tie_break_with_line_number: strategy='exact (ignoring whitespace)', hint=Some(29), entropy=true
trace:       No exact (ignoring whitespace) matches found.
trace:     Strategy 2 (Whitespace-insensitive): no match found.
debug:     Strategy 3 (Fuzzy): beginning flexible window fuzzy search (threshold=0.70, match block len=0.7)
trace:       Hunk match block (8 lines): ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "- ", "2.20.1"]
trace:       Searching with window sizes from 5 to 32 (hunk size: 8, fuzz distance: 24)
debug:       find_search_ranges: analyzing 8 match line(s) against 203 target line(s).
trace:         Identified 5 high-entropy candidate anchor line(s) (search_radius=16, max candidates to test=100)
debug:         Spatial consensus: 4 anchor(s) agree on start near line 38
debug:       Found anchor line (hunk line 5) with 1 occurrences.
trace:         Anchor text: '#include <drm/drm_crtc_helper.h>'
trace:         Occurrence at target line 33: window estimated [13..76] (search radius +/-16)
trace:         Raw ranges before merging: [(12, 76)]
trace: merge_ranges: merging 1 input range(s): [(12, 76)]
trace: merge_ranges: result 1 disjoint range(s): [(12, 76)]
debug:       Search ranges merged: 1 disjoint range(s) covering 64/203 line(s) (68.5% pruned): [(12, 76)]
trace:     Using search ranges: [(12, 76)]
debug:       compute_scored_windows (parallel): evaluating 1302 candidate window(s) across 1 range(s) (window lengths 5..=32)
trace:         Match block length: 8, Target line count: 203, Search ranges: [(12, 76)]
trace:         score_window: window_len=19, match_len=8, line_score=0.349, ratio_lines=0.222, final_score=0.349
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=20, match_len=8, line_score=0.463, ratio_lines=0.286, final_score=0.463
trace:         score_window: window_len=21, match_len=8, line_score=0.574, ratio_lines=0.345, final_score=0.574
trace:         score_window: window_len=22, match_len=8, line_score=0.684, ratio_lines=0.400, final_score=0.684
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=23, match_len=8, line_score=0.680, ratio_lines=0.387, final_score=0.680
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.308
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=24, match_len=8, line_score=0.675, ratio_lines=0.375, final_score=0.675
trace:         score_window: window_len=25, match_len=8, line_score=0.670, ratio_lines=0.364, final_score=0.670
trace:         score_window: window_len=26, match_len=8, line_score=0.666, ratio_lines=0.353, final_score=0.666
trace:         score_window: window_len=27, match_len=8, line_score=0.661, ratio_lines=0.343, final_score=0.661
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=28, match_len=8, line_score=0.656, ratio_lines=0.333, final_score=0.656
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=29, match_len=8, line_score=0.652, ratio_lines=0.324, final_score=0.652
trace:         score_window: window_len=30, match_len=8, line_score=0.647, ratio_lines=0.316, final_score=0.647
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=31, match_len=8, line_score=0.642, ratio_lines=0.308, final_score=0.642
trace:         score_window: window_len=32, match_len=8, line_score=0.638, ratio_lines=0.300, final_score=0.638
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=18, match_len=8, line_score=0.352, ratio_lines=0.231, final_score=0.352
trace:         score_window: window_len=19, match_len=8, line_score=0.466, ratio_lines=0.296, final_score=0.466
trace:         score_window: window_len=20, match_len=8, line_score=0.578, ratio_lines=0.357, final_score=0.578
trace:         score_window: window_len=21, match_len=8, line_score=0.689, ratio_lines=0.414, final_score=0.689
trace:         score_window: window_len=22, match_len=8, line_score=0.684, ratio_lines=0.400, final_score=0.684
trace:         score_window: window_len=23, match_len=8, line_score=0.680, ratio_lines=0.387, final_score=0.680
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=24, match_len=8, line_score=0.675, ratio_lines=0.375, final_score=0.675
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.308
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=25, match_len=8, line_score=0.670, ratio_lines=0.364, final_score=0.670
trace:         score_window: window_len=26, match_len=8, line_score=0.666, ratio_lines=0.353, final_score=0.666
trace:         score_window: window_len=27, match_len=8, line_score=0.661, ratio_lines=0.343, final_score=0.661
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=28, match_len=8, line_score=0.656, ratio_lines=0.333, final_score=0.656
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=29, match_len=8, line_score=0.652, ratio_lines=0.324, final_score=0.652
trace:         score_window: window_len=30, match_len=8, line_score=0.647, ratio_lines=0.316, final_score=0.647
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=31, match_len=8, line_score=0.642, ratio_lines=0.308, final_score=0.642
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=32, match_len=8, line_score=0.638, ratio_lines=0.300, final_score=0.638
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.308
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=17, match_len=8, line_score=0.354, ratio_lines=0.240, final_score=0.354
trace:         score_window: window_len=18, match_len=8, line_score=0.469, ratio_lines=0.308, final_score=0.469
trace:         score_window: window_len=19, match_len=8, line_score=0.582, ratio_lines=0.370, final_score=0.582
trace:         score_window: window_len=20, match_len=8, line_score=0.694, ratio_lines=0.429, final_score=0.694
trace:         score_window: window_len=21, match_len=8, line_score=0.689, ratio_lines=0.414, final_score=0.689
trace:         score_window: window_len=22, match_len=8, line_score=0.684, ratio_lines=0.400, final_score=0.684
trace:         score_window: window_len=23, match_len=8, line_score=0.680, ratio_lines=0.387, final_score=0.680
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=24, match_len=8, line_score=0.675, ratio_lines=0.375, final_score=0.675
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=25, match_len=8, line_score=0.670, ratio_lines=0.364, final_score=0.670
trace:         score_window: window_len=26, match_len=8, line_score=0.666, ratio_lines=0.353, final_score=0.666
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=27, match_len=8, line_score=0.661, ratio_lines=0.343, final_score=0.661
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=28, match_len=8, line_score=0.656, ratio_lines=0.333, final_score=0.656
trace:         score_window: window_len=29, match_len=8, line_score=0.652, ratio_lines=0.324, final_score=0.652
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=30, match_len=8, line_score=0.647, ratio_lines=0.316, final_score=0.647
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.308
trace:         score_window: window_len=31, match_len=8, line_score=0.642, ratio_lines=0.308, final_score=0.642
trace:         score_window: window_len=32, match_len=8, line_score=0.638, ratio_lines=0.300, final_score=0.638
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=12, match_len=8, line_score=0.244, ratio_lines=0.200, final_score=0.244
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=13, match_len=8, line_score=0.242, ratio_lines=0.190, final_score=0.242
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=16, match_len=8, line_score=0.356, ratio_lines=0.250, final_score=0.356
trace:         score_window: window_len=17, match_len=8, line_score=0.472, ratio_lines=0.320, final_score=0.472
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=18, match_len=8, line_score=0.586, ratio_lines=0.385, final_score=0.586
trace:         score_window: window_len=19, match_len=8, line_score=0.698, ratio_lines=0.444, final_score=0.698
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=20, match_len=8, line_score=0.694, ratio_lines=0.429, final_score=0.694
trace:         score_window: window_len=21, match_len=8, line_score=0.689, ratio_lines=0.414, final_score=0.689
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=22, match_len=8, line_score=0.684, ratio_lines=0.400, final_score=0.684
trace:         score_window: window_len=23, match_len=8, line_score=0.680, ratio_lines=0.387, final_score=0.680
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=24, match_len=8, line_score=0.675, ratio_lines=0.375, final_score=0.675
trace:         score_window: window_len=25, match_len=8, line_score=0.670, ratio_lines=0.364, final_score=0.670
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=26, match_len=8, line_score=0.666, ratio_lines=0.353, final_score=0.666
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.308
trace:         score_window: window_len=27, match_len=8, line_score=0.661, ratio_lines=0.343, final_score=0.661
trace:         score_window: window_len=28, match_len=8, line_score=0.656, ratio_lines=0.333, final_score=0.656
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=29, match_len=8, line_score=0.652, ratio_lines=0.324, final_score=0.652
trace:         score_window: window_len=30, match_len=8, line_score=0.647, ratio_lines=0.316, final_score=0.647
trace:         score_window: window_len=12, match_len=8, line_score=0.244, ratio_lines=0.200, final_score=0.244
trace:         score_window: window_len=31, match_len=8, line_score=0.642, ratio_lines=0.308, final_score=0.642
trace:         score_window: window_len=32, match_len=8, line_score=0.638, ratio_lines=0.300, final_score=0.638
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=15, match_len=8, line_score=0.359, ratio_lines=0.261, final_score=0.359
trace:         score_window: window_len=16, match_len=8, line_score=0.475, ratio_lines=0.333, final_score=0.475
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=17, match_len=8, line_score=0.590, ratio_lines=0.400, final_score=0.590
trace:         score_window: window_len=19, match_len=8, line_score=0.698, ratio_lines=0.444, final_score=0.698
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=20, match_len=8, line_score=0.694, ratio_lines=0.429, final_score=0.694
trace:         score_window: window_len=21, match_len=8, line_score=0.689, ratio_lines=0.414, final_score=0.689
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=22, match_len=8, line_score=0.684, ratio_lines=0.400, final_score=0.684
trace:         score_window: window_len=23, match_len=8, line_score=0.680, ratio_lines=0.387, final_score=0.680
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.308
trace:         score_window: window_len=24, match_len=8, line_score=0.675, ratio_lines=0.375, final_score=0.675
trace:         score_window: window_len=25, match_len=8, line_score=0.670, ratio_lines=0.364, final_score=0.670
trace:         score_window: window_len=26, match_len=8, line_score=0.666, ratio_lines=0.353, final_score=0.666
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=27, match_len=8, line_score=0.661, ratio_lines=0.343, final_score=0.661
trace:         score_window: window_len=28, match_len=8, line_score=0.656, ratio_lines=0.333, final_score=0.656
trace:         score_window: window_len=29, match_len=8, line_score=0.652, ratio_lines=0.324, final_score=0.652
trace:         score_window: window_len=30, match_len=8, line_score=0.647, ratio_lines=0.316, final_score=0.647
trace:         score_window: window_len=31, match_len=8, line_score=0.642, ratio_lines=0.308, final_score=0.642
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=32, match_len=8, line_score=0.638, ratio_lines=0.300, final_score=0.638
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.161
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=14, match_len=8, line_score=0.361, ratio_lines=0.273, final_score=0.361
trace:         score_window: window_len=15, match_len=8, line_score=0.478, ratio_lines=0.348, final_score=0.478
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=16, match_len=8, line_score=0.594, ratio_lines=0.417, final_score=0.594
trace:         score_window: window_len=19, match_len=8, line_score=0.698, ratio_lines=0.444, final_score=0.698
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.308
trace:         score_window: window_len=20, match_len=8, line_score=0.694, ratio_lines=0.429, final_score=0.694
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=21, match_len=8, line_score=0.689, ratio_lines=0.414, final_score=0.689
trace:         score_window: window_len=22, match_len=8, line_score=0.684, ratio_lines=0.400, final_score=0.684
trace:         score_window: window_len=23, match_len=8, line_score=0.680, ratio_lines=0.387, final_score=0.680
trace:         score_window: window_len=24, match_len=8, line_score=0.675, ratio_lines=0.375, final_score=0.675
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.308
trace:         score_window: window_len=25, match_len=8, line_score=0.670, ratio_lines=0.364, final_score=0.670
trace:         score_window: window_len=26, match_len=8, line_score=0.666, ratio_lines=0.353, final_score=0.666
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=27, match_len=8, line_score=0.661, ratio_lines=0.343, final_score=0.661
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.250
trace:         score_window: window_len=28, match_len=8, line_score=0.656, ratio_lines=0.333, final_score=0.656
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.298
trace:         score_window: window_len=29, match_len=8, line_score=0.652, ratio_lines=0.324, final_score=0.652
trace:         score_window: window_len=30, match_len=8, line_score=0.647, ratio_lines=0.316, final_score=0.647
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.253
trace:         score_window: window_len=31, match_len=8, line_score=0.642, ratio_lines=0.308, final_score=0.642
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.311
trace:         score_window: window_len=32, match_len=8, line_score=0.638, ratio_lines=0.300, final_score=0.638
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.280
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.200
trace:         score_window: window_len=13, match_len=8, line_score=0.363, ratio_lines=0.286, final_score=0.363
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=14, match_len=8, line_score=0.481, ratio_lines=0.364, final_score=0.481
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=15, match_len=8, line_score=0.598, ratio_lines=0.435, final_score=0.598
trace:         score_window: window_len=19, match_len=8, line_score=0.698, ratio_lines=0.444, final_score=0.698
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.308
trace:         score_window: window_len=20, match_len=8, line_score=0.694, ratio_lines=0.429, final_score=0.694
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=21, match_len=8, line_score=0.689, ratio_lines=0.414, final_score=0.689
trace:         score_window: window_len=22, match_len=8, line_score=0.684, ratio_lines=0.400, final_score=0.684
trace:         score_window: window_len=23, match_len=8, line_score=0.680, ratio_lines=0.387, final_score=0.680
trace:         score_window: window_len=24, match_len=8, line_score=0.675, ratio_lines=0.375, final_score=0.675
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.280
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.280
trace:         score_window: window_len=25, match_len=8, line_score=0.670, ratio_lines=0.364, final_score=0.670
trace:         score_window: window_len=26, match_len=8, line_score=0.666, ratio_lines=0.353, final_score=0.666
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.304
trace:         score_window: window_len=27, match_len=8, line_score=0.661, ratio_lines=0.343, final_score=0.661
trace:         score_window: window_len=28, match_len=8, line_score=0.656, ratio_lines=0.333, final_score=0.656
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.318
trace:         score_window: window_len=29, match_len=8, line_score=0.652, ratio_lines=0.324, final_score=0.652
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=30, match_len=8, line_score=0.647, ratio_lines=0.316, final_score=0.647
trace:         score_window: window_len=31, match_len=8, line_score=0.642, ratio_lines=0.308, final_score=0.642
trace:         score_window: window_len=32, match_len=8, line_score=0.638, ratio_lines=0.300, final_score=0.638
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.336
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.290
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.323
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.312
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.318
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.303
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.326
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=12, match_len=8, line_score=0.366, ratio_lines=0.300, final_score=0.366
trace:         score_window: window_len=13, match_len=8, line_score=0.484, ratio_lines=0.381, final_score=0.484
trace:         score_window: window_len=14, match_len=8, line_score=0.602, ratio_lines=0.455, final_score=0.602
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=19, match_len=8, line_score=0.698, ratio_lines=0.444, final_score=0.698
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=20, match_len=8, line_score=0.694, ratio_lines=0.429, final_score=0.694
trace:         score_window: window_len=21, match_len=8, line_score=0.689, ratio_lines=0.414, final_score=0.689
trace:         score_window: window_len=22, match_len=8, line_score=0.684, ratio_lines=0.400, final_score=0.684
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=23, match_len=8, line_score=0.680, ratio_lines=0.387, final_score=0.680
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.298
trace:         score_window: window_len=24, match_len=8, line_score=0.675, ratio_lines=0.375, final_score=0.675
trace:         score_window: window_len=25, match_len=8, line_score=0.670, ratio_lines=0.364, final_score=0.670
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.308
trace:         score_window: window_len=26, match_len=8, line_score=0.666, ratio_lines=0.353, final_score=0.666
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=27, match_len=8, line_score=0.661, ratio_lines=0.343, final_score=0.661
trace:         score_window: window_len=28, match_len=8, line_score=0.656, ratio_lines=0.333, final_score=0.656
trace:         score_window: window_len=29, match_len=8, line_score=0.652, ratio_lines=0.324, final_score=0.652
trace:         score_window: window_len=30, match_len=8, line_score=0.647, ratio_lines=0.316, final_score=0.647
trace:         score_window: window_len=8, match_len=8, line_score=0.125, ratio_lines=0.125, final_score=0.138
trace:         score_window: window_len=31, match_len=8, line_score=0.642, ratio_lines=0.308, final_score=0.642
trace:         score_window: window_len=7, match_len=8, line_score=0.133, ratio_lines=0.133, final_score=0.162
trace:         score_window: window_len=32, match_len=8, line_score=0.638, ratio_lines=0.300, final_score=0.638
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.337
trace:         score_window: window_len=6, match_len=8, line_score=0.143, ratio_lines=0.143, final_score=0.170
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.365
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.221
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.319
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.263
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.308
trace:         score_window: window_len=11, match_len=8, line_score=0.368, ratio_lines=0.316, final_score=0.380
trace:         score_window: window_len=12, match_len=8, line_score=0.488, ratio_lines=0.400, final_score=0.488
trace:         score_window: window_len=13, match_len=8, line_score=0.605, ratio_lines=0.476, final_score=0.605
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=19, match_len=8, line_score=0.698, ratio_lines=0.444, final_score=0.698
trace:         score_window: window_len=20, match_len=8, line_score=0.694, ratio_lines=0.429, final_score=0.694
trace:         score_window: window_len=7, match_len=8, line_score=0.133, ratio_lines=0.133, final_score=0.133
trace:         score_window: window_len=21, match_len=8, line_score=0.689, ratio_lines=0.414, final_score=0.689
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=22, match_len=8, line_score=0.684, ratio_lines=0.400, final_score=0.684
trace:         score_window: window_len=6, match_len=8, line_score=0.143, ratio_lines=0.143, final_score=0.150
trace:         score_window: window_len=23, match_len=8, line_score=0.680, ratio_lines=0.387, final_score=0.680
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=24, match_len=8, line_score=0.675, ratio_lines=0.375, final_score=0.675
trace:         score_window: window_len=25, match_len=8, line_score=0.670, ratio_lines=0.364, final_score=0.670
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.154
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=26, match_len=8, line_score=0.666, ratio_lines=0.353, final_score=0.666
trace:         score_window: window_len=27, match_len=8, line_score=0.661, ratio_lines=0.343, final_score=0.661
trace:         score_window: window_len=28, match_len=8, line_score=0.656, ratio_lines=0.333, final_score=0.656
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=29, match_len=8, line_score=0.652, ratio_lines=0.324, final_score=0.652
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=30, match_len=8, line_score=0.647, ratio_lines=0.316, final_score=0.647
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=31, match_len=8, line_score=0.642, ratio_lines=0.308, final_score=0.642
trace:         score_window: window_len=32, match_len=8, line_score=0.638, ratio_lines=0.300, final_score=0.638
trace:         score_window: window_len=6, match_len=8, line_score=0.143, ratio_lines=0.143, final_score=0.201
trace:         score_window: window_len=8, match_len=8, line_score=0.125, ratio_lines=0.125, final_score=0.436
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.341
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.271
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.242
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.370
trace:         score_window: window_len=10, match_len=8, line_score=0.370, ratio_lines=0.333, final_score=0.391
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.381
trace:         score_window: window_len=11, match_len=8, line_score=0.491, ratio_lines=0.421, final_score=0.491
trace:         score_window: window_len=12, match_len=8, line_score=0.609, ratio_lines=0.500, final_score=0.609
trace:         score_window: window_len=19, match_len=8, line_score=0.698, ratio_lines=0.444, final_score=0.698
trace:         score_window: window_len=20, match_len=8, line_score=0.694, ratio_lines=0.429, final_score=0.694
trace:         score_window: window_len=6, match_len=8, line_score=0.143, ratio_lines=0.143, final_score=0.228
trace:         score_window: window_len=21, match_len=8, line_score=0.689, ratio_lines=0.414, final_score=0.689
trace:         score_window: window_len=22, match_len=8, line_score=0.684, ratio_lines=0.400, final_score=0.684
trace:         score_window: window_len=5, match_len=8, line_score=0.000, ratio_lines=0.000, final_score=0.188
trace:         score_window: window_len=23, match_len=8, line_score=0.680, ratio_lines=0.387, final_score=0.680
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=24, match_len=8, line_score=0.675, ratio_lines=0.375, final_score=0.675
trace:         score_window: window_len=25, match_len=8, line_score=0.670, ratio_lines=0.364, final_score=0.670
trace:         score_window: window_len=26, match_len=8, line_score=0.666, ratio_lines=0.353, final_score=0.666
trace:         score_window: window_len=6, match_len=8, line_score=0.143, ratio_lines=0.143, final_score=0.231
trace:         score_window: window_len=27, match_len=8, line_score=0.661, ratio_lines=0.343, final_score=0.661
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.256
trace:         score_window: window_len=28, match_len=8, line_score=0.656, ratio_lines=0.333, final_score=0.656
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.189
trace:         score_window: window_len=29, match_len=8, line_score=0.652, ratio_lines=0.324, final_score=0.652
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=30, match_len=8, line_score=0.647, ratio_lines=0.316, final_score=0.647
trace:         score_window: window_len=31, match_len=8, line_score=0.642, ratio_lines=0.308, final_score=0.642
trace:         score_window: window_len=8, match_len=8, line_score=0.125, ratio_lines=0.125, final_score=0.226
trace:         score_window: window_len=32, match_len=8, line_score=0.638, ratio_lines=0.300, final_score=0.638
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.279
trace:         score_window: window_len=7, match_len=8, line_score=0.133, ratio_lines=0.133, final_score=0.236
trace:         score_window: window_len=7, match_len=8, line_score=0.133, ratio_lines=0.133, final_score=0.437
trace:         score_window: window_len=9, match_len=8, line_score=0.373, ratio_lines=0.353, final_score=0.402
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.342
trace:         score_window: window_len=10, match_len=8, line_score=0.494, ratio_lines=0.444, final_score=0.494
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.255
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.372
trace:         score_window: window_len=11, match_len=8, line_score=0.613, ratio_lines=0.526, final_score=0.613
trace:         score_window: window_len=6, match_len=8, line_score=0.143, ratio_lines=0.143, final_score=0.247
trace:         score_window: window_len=19, match_len=8, line_score=0.698, ratio_lines=0.444, final_score=0.698
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=20, match_len=8, line_score=0.694, ratio_lines=0.429, final_score=0.694
trace:         score_window: window_len=21, match_len=8, line_score=0.689, ratio_lines=0.414, final_score=0.689
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.229
trace:         score_window: window_len=22, match_len=8, line_score=0.684, ratio_lines=0.400, final_score=0.684
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=23, match_len=8, line_score=0.680, ratio_lines=0.387, final_score=0.680
trace:         score_window: window_len=24, match_len=8, line_score=0.675, ratio_lines=0.375, final_score=0.675
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.280
trace:         score_window: window_len=25, match_len=8, line_score=0.670, ratio_lines=0.364, final_score=0.670
trace:         score_window: window_len=26, match_len=8, line_score=0.666, ratio_lines=0.353, final_score=0.666
trace:         score_window: window_len=7, match_len=8, line_score=0.133, ratio_lines=0.133, final_score=0.250
trace:         score_window: window_len=27, match_len=8, line_score=0.661, ratio_lines=0.343, final_score=0.661
trace:         score_window: window_len=28, match_len=8, line_score=0.656, ratio_lines=0.333, final_score=0.656
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=29, match_len=8, line_score=0.652, ratio_lines=0.324, final_score=0.652
trace:         score_window: window_len=6, match_len=8, line_score=0.143, ratio_lines=0.143, final_score=0.264
trace:         score_window: window_len=30, match_len=8, line_score=0.647, ratio_lines=0.316, final_score=0.647
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=31, match_len=8, line_score=0.642, ratio_lines=0.308, final_score=0.642
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.279
trace:         score_window: window_len=32, match_len=8, line_score=0.638, ratio_lines=0.300, final_score=0.638
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=8, match_len=8, line_score=0.375, ratio_lines=0.375, final_score=0.521
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.383
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=9, match_len=8, line_score=0.497, ratio_lines=0.471, final_score=0.531
trace:         score_window: window_len=6, match_len=8, line_score=0.143, ratio_lines=0.143, final_score=0.283
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.295
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=10, match_len=8, line_score=0.617, ratio_lines=0.556, final_score=0.665
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.433
trace:         score_window: window_len=6, match_len=8, line_score=0.143, ratio_lines=0.143, final_score=0.264
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=19, match_len=8, line_score=0.698, ratio_lines=0.444, final_score=0.698
trace:         score_window: window_len=20, match_len=8, line_score=0.694, ratio_lines=0.429, final_score=0.694
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.279
trace:         score_window: window_len=21, match_len=8, line_score=0.689, ratio_lines=0.414, final_score=0.689
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=22, match_len=8, line_score=0.684, ratio_lines=0.400, final_score=0.684
trace:         score_window: window_len=23, match_len=8, line_score=0.680, ratio_lines=0.387, final_score=0.680
trace:         score_window: window_len=24, match_len=8, line_score=0.675, ratio_lines=0.375, final_score=0.675
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.254
trace:         score_window: window_len=25, match_len=8, line_score=0.670, ratio_lines=0.364, final_score=0.670
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=26, match_len=8, line_score=0.666, ratio_lines=0.353, final_score=0.666
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=27, match_len=8, line_score=0.661, ratio_lines=0.343, final_score=0.661
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=28, match_len=8, line_score=0.656, ratio_lines=0.333, final_score=0.656
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=29, match_len=8, line_score=0.652, ratio_lines=0.324, final_score=0.652
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.239
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=30, match_len=8, line_score=0.647, ratio_lines=0.316, final_score=0.647
trace:         score_window: window_len=31, match_len=8, line_score=0.642, ratio_lines=0.308, final_score=0.642
trace:         score_window: window_len=7, match_len=8, line_score=0.133, ratio_lines=0.133, final_score=0.223
trace:         score_window: window_len=32, match_len=8, line_score=0.638, ratio_lines=0.300, final_score=0.638
trace:         score_window: window_len=8, match_len=8, line_score=0.500, ratio_lines=0.500, final_score=0.541
trace:         score_window: window_len=6, match_len=8, line_score=0.143, ratio_lines=0.143, final_score=0.218
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=7, match_len=8, line_score=0.400, ratio_lines=0.400, final_score=0.524
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.239
trace:         score_window: window_len=9, match_len=8, line_score=0.621, ratio_lines=0.588, final_score=0.668
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.385
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.252
trace:         score_window: window_len=8, match_len=8, line_score=0.125, ratio_lines=0.125, final_score=0.178
trace:         score_window: window_len=19, match_len=8, line_score=0.698, ratio_lines=0.444, final_score=0.698
trace:         score_window: window_len=20, match_len=8, line_score=0.694, ratio_lines=0.429, final_score=0.694
trace:         score_window: window_len=21, match_len=8, line_score=0.689, ratio_lines=0.414, final_score=0.689
trace:         score_window: window_len=7, match_len=8, line_score=0.133, ratio_lines=0.133, final_score=0.186
trace:         score_window: window_len=22, match_len=8, line_score=0.684, ratio_lines=0.400, final_score=0.684
trace:         score_window: window_len=23, match_len=8, line_score=0.680, ratio_lines=0.387, final_score=0.680
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=24, match_len=8, line_score=0.675, ratio_lines=0.375, final_score=0.675
trace:         score_window: window_len=25, match_len=8, line_score=0.670, ratio_lines=0.364, final_score=0.670
trace:         score_window: window_len=6, match_len=8, line_score=0.143, ratio_lines=0.143, final_score=0.210
trace:         score_window: window_len=26, match_len=8, line_score=0.666, ratio_lines=0.353, final_score=0.666
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=27, match_len=8, line_score=0.661, ratio_lines=0.343, final_score=0.661
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.202
trace:         score_window: window_len=28, match_len=8, line_score=0.656, ratio_lines=0.333, final_score=0.656
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=29, match_len=8, line_score=0.652, ratio_lines=0.324, final_score=0.652
trace:         score_window: window_len=30, match_len=8, line_score=0.647, ratio_lines=0.316, final_score=0.647
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=31, match_len=8, line_score=0.642, ratio_lines=0.308, final_score=0.642
trace:         score_window: window_len=7, match_len=8, line_score=0.133, ratio_lines=0.133, final_score=0.168
trace:         score_window: window_len=32, match_len=8, line_score=0.638, ratio_lines=0.300, final_score=0.638
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=8, match_len=8, line_score=0.625, ratio_lines=0.625, final_score=0.765
trace:         score_window: window_len=7, match_len=8, line_score=0.533, ratio_lines=0.533, final_score=0.620
trace:         score_window: window_len=6, match_len=8, line_score=0.143, ratio_lines=0.143, final_score=0.171
trace:         score_window: window_len=6, match_len=8, line_score=0.429, ratio_lines=0.429, final_score=0.609
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.455
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.186
trace:         score_window: window_len=19, match_len=8, line_score=0.698, ratio_lines=0.444, final_score=0.698
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=20, match_len=8, line_score=0.694, ratio_lines=0.429, final_score=0.694
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=21, match_len=8, line_score=0.689, ratio_lines=0.414, final_score=0.689
trace:         score_window: window_len=22, match_len=8, line_score=0.684, ratio_lines=0.400, final_score=0.684
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=6, match_len=8, line_score=0.143, ratio_lines=0.143, final_score=0.146
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.154
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=23, match_len=8, line_score=0.680, ratio_lines=0.387, final_score=0.680
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=24, match_len=8, line_score=0.675, ratio_lines=0.375, final_score=0.675
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=25, match_len=8, line_score=0.670, ratio_lines=0.364, final_score=0.670
trace:         score_window: window_len=26, match_len=8, line_score=0.666, ratio_lines=0.353, final_score=0.666
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.202
trace:         score_window: window_len=27, match_len=8, line_score=0.661, ratio_lines=0.343, final_score=0.661
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.264
trace:         score_window: window_len=28, match_len=8, line_score=0.656, ratio_lines=0.333, final_score=0.656
trace:         score_window: window_len=29, match_len=8, line_score=0.652, ratio_lines=0.324, final_score=0.652
trace:         score_window: window_len=7, match_len=8, line_score=0.133, ratio_lines=0.133, final_score=0.228
trace:         score_window: window_len=30, match_len=8, line_score=0.647, ratio_lines=0.316, final_score=0.647
trace:         score_window: window_len=31, match_len=8, line_score=0.642, ratio_lines=0.308, final_score=0.642
trace:         score_window: window_len=6, match_len=8, line_score=0.143, ratio_lines=0.143, final_score=0.256
trace:         score_window: window_len=32, match_len=8, line_score=0.638, ratio_lines=0.300, final_score=0.638
trace:         score_window: window_len=7, match_len=8, line_score=0.667, ratio_lines=0.667, final_score=0.700
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.256
trace:         score_window: window_len=6, match_len=8, line_score=0.571, ratio_lines=0.571, final_score=0.624
trace:         score_window: window_len=5, match_len=8, line_score=0.462, ratio_lines=0.462, final_score=0.613
trace:         score_window: window_len=6, match_len=8, line_score=0.143, ratio_lines=0.143, final_score=0.195
trace:         score_window: window_len=19, match_len=8, line_score=0.698, ratio_lines=0.444, final_score=0.698
trace:         score_window: window_len=20, match_len=8, line_score=0.694, ratio_lines=0.429, final_score=0.694
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.221
trace:         score_window: window_len=21, match_len=8, line_score=0.689, ratio_lines=0.414, final_score=0.689
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.154
trace:         score_window: window_len=22, match_len=8, line_score=0.684, ratio_lines=0.400, final_score=0.684
trace:         score_window: window_len=5, match_len=8, line_score=0.615, ratio_lines=0.615, final_score=0.696
trace:         score_window: window_len=23, match_len=8, line_score=0.680, ratio_lines=0.387, final_score=0.680
trace:         score_window: window_len=24, match_len=8, line_score=0.675, ratio_lines=0.375, final_score=0.675
trace:         score_window: window_len=19, match_len=8, line_score=0.698, ratio_lines=0.444, final_score=0.698
trace:         score_window: window_len=20, match_len=8, line_score=0.694, ratio_lines=0.429, final_score=0.694
trace:         score_window: window_len=25, match_len=8, line_score=0.670, ratio_lines=0.364, final_score=0.670
trace:         score_window: window_len=21, match_len=8, line_score=0.689, ratio_lines=0.414, final_score=0.689
trace:         score_window: window_len=26, match_len=8, line_score=0.666, ratio_lines=0.353, final_score=0.666
trace:         score_window: window_len=22, match_len=8, line_score=0.684, ratio_lines=0.400, final_score=0.684
trace:         score_window: window_len=27, match_len=8, line_score=0.661, ratio_lines=0.343, final_score=0.661
trace:         score_window: window_len=23, match_len=8, line_score=0.680, ratio_lines=0.387, final_score=0.680
trace:         score_window: window_len=28, match_len=8, line_score=0.656, ratio_lines=0.333, final_score=0.656
trace:         score_window: window_len=24, match_len=8, line_score=0.675, ratio_lines=0.375, final_score=0.675
trace:         score_window: window_len=29, match_len=8, line_score=0.652, ratio_lines=0.324, final_score=0.652
trace:         score_window: window_len=25, match_len=8, line_score=0.670, ratio_lines=0.364, final_score=0.670
trace:         score_window: window_len=30, match_len=8, line_score=0.647, ratio_lines=0.316, final_score=0.647
trace:         score_window: window_len=26, match_len=8, line_score=0.666, ratio_lines=0.353, final_score=0.666
trace:         score_window: window_len=31, match_len=8, line_score=0.642, ratio_lines=0.308, final_score=0.642
trace:         score_window: window_len=27, match_len=8, line_score=0.661, ratio_lines=0.343, final_score=0.661
trace:         score_window: window_len=32, match_len=8, line_score=0.638, ratio_lines=0.300, final_score=0.638
trace:         score_window: window_len=28, match_len=8, line_score=0.656, ratio_lines=0.333, final_score=0.656
trace:         score_window: window_len=29, match_len=8, line_score=0.652, ratio_lines=0.324, final_score=0.652
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.259
trace:         score_window: window_len=30, match_len=8, line_score=0.647, ratio_lines=0.316, final_score=0.647
trace:         score_window: window_len=31, match_len=8, line_score=0.642, ratio_lines=0.308, final_score=0.642
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=32, match_len=8, line_score=0.638, ratio_lines=0.300, final_score=0.638
trace:         score_window: window_len=19, match_len=8, line_score=0.698, ratio_lines=0.444, final_score=0.698
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=20, match_len=8, line_score=0.694, ratio_lines=0.429, final_score=0.694
trace:         score_window: window_len=21, match_len=8, line_score=0.689, ratio_lines=0.414, final_score=0.689
trace:         score_window: window_len=22, match_len=8, line_score=0.684, ratio_lines=0.400, final_score=0.684
trace:         score_window: window_len=23, match_len=8, line_score=0.680, ratio_lines=0.387, final_score=0.680
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=24, match_len=8, line_score=0.675, ratio_lines=0.375, final_score=0.675
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=25, match_len=8, line_score=0.670, ratio_lines=0.364, final_score=0.670
trace:         score_window: window_len=26, match_len=8, line_score=0.666, ratio_lines=0.353, final_score=0.666
trace:         score_window: window_len=27, match_len=8, line_score=0.661, ratio_lines=0.343, final_score=0.661
trace:         score_window: window_len=28, match_len=8, line_score=0.656, ratio_lines=0.333, final_score=0.656
trace:         score_window: window_len=5, match_len=8, line_score=0.154, ratio_lines=0.154, final_score=0.214
trace:         score_window: window_len=29, match_len=8, line_score=0.652, ratio_lines=0.324, final_score=0.652
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=30, match_len=8, line_score=0.647, ratio_lines=0.316, final_score=0.647
trace:         score_window: window_len=31, match_len=8, line_score=0.642, ratio_lines=0.308, final_score=0.642
trace:         score_window: window_len=32, match_len=8, line_score=0.638, ratio_lines=0.300, final_score=0.638
trace:         score_window: window_len=8, match_len=8, line_score=0.625, ratio_lines=0.625, final_score=0.625
trace:         score_window: window_len=7, match_len=8, line_score=0.667, ratio_lines=0.667, final_score=0.667
trace:         score_window: window_len=9, match_len=8, line_score=0.621, ratio_lines=0.588, final_score=0.621
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=10, match_len=8, line_score=0.617, ratio_lines=0.556, final_score=0.617
trace:         score_window: window_len=11, match_len=8, line_score=0.613, ratio_lines=0.526, final_score=0.613
trace:         score_window: window_len=12, match_len=8, line_score=0.609, ratio_lines=0.500, final_score=0.609
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=13, match_len=8, line_score=0.605, ratio_lines=0.476, final_score=0.605
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=14, match_len=8, line_score=0.602, ratio_lines=0.455, final_score=0.602
trace:         score_window: window_len=15, match_len=8, line_score=0.598, ratio_lines=0.435, final_score=0.598
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=16, match_len=8, line_score=0.594, ratio_lines=0.417, final_score=0.594
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=17, match_len=8, line_score=0.590, ratio_lines=0.400, final_score=0.590
trace:         score_window: window_len=18, match_len=8, line_score=0.586, ratio_lines=0.385, final_score=0.586
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.308
trace:         score_window: window_len=19, match_len=8, line_score=0.582, ratio_lines=0.370, final_score=0.582
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=20, match_len=8, line_score=0.578, ratio_lines=0.357, final_score=0.578
trace:         score_window: window_len=21, match_len=8, line_score=0.574, ratio_lines=0.345, final_score=0.574
trace:         score_window: window_len=22, match_len=8, line_score=0.570, ratio_lines=0.333, final_score=0.570
trace:         score_window: window_len=23, match_len=8, line_score=0.566, ratio_lines=0.323, final_score=0.566
trace:         score_window: window_len=24, match_len=8, line_score=0.562, ratio_lines=0.312, final_score=0.562
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=25, match_len=8, line_score=0.559, ratio_lines=0.303, final_score=0.559
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=26, match_len=8, line_score=0.555, ratio_lines=0.294, final_score=0.555
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=27, match_len=8, line_score=0.551, ratio_lines=0.286, final_score=0.551
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=28, match_len=8, line_score=0.547, ratio_lines=0.278, final_score=0.547
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=29, match_len=8, line_score=0.543, ratio_lines=0.270, final_score=0.543
trace:         score_window: window_len=30, match_len=8, line_score=0.539, ratio_lines=0.263, final_score=0.539
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.308
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=31, match_len=8, line_score=0.535, ratio_lines=0.256, final_score=0.535
trace:         score_window: window_len=32, match_len=8, line_score=0.531, ratio_lines=0.250, final_score=0.531
trace:         score_window: window_len=8, match_len=8, line_score=0.500, ratio_lines=0.500, final_score=0.500
trace:         score_window: window_len=7, match_len=8, line_score=0.533, ratio_lines=0.533, final_score=0.533
trace:         score_window: window_len=9, match_len=8, line_score=0.497, ratio_lines=0.471, final_score=0.497
trace:         score_window: window_len=6, match_len=8, line_score=0.571, ratio_lines=0.571, final_score=0.571
trace:         score_window: window_len=10, match_len=8, line_score=0.494, ratio_lines=0.444, final_score=0.494
trace:         score_window: window_len=5, match_len=8, line_score=0.615, ratio_lines=0.615, final_score=0.615
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=11, match_len=8, line_score=0.491, ratio_lines=0.421, final_score=0.491
trace:         score_window: window_len=12, match_len=8, line_score=0.488, ratio_lines=0.400, final_score=0.488
trace:         score_window: window_len=13, match_len=8, line_score=0.484, ratio_lines=0.381, final_score=0.484
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=14, match_len=8, line_score=0.481, ratio_lines=0.364, final_score=0.481
trace:         score_window: window_len=15, match_len=8, line_score=0.478, ratio_lines=0.348, final_score=0.478
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=16, match_len=8, line_score=0.475, ratio_lines=0.333, final_score=0.475
trace:         score_window: window_len=17, match_len=8, line_score=0.472, ratio_lines=0.320, final_score=0.472
trace:         score_window: window_len=18, match_len=8, line_score=0.469, ratio_lines=0.308, final_score=0.469
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.291
trace:         score_window: window_len=19, match_len=8, line_score=0.466, ratio_lines=0.296, final_score=0.466
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=20, match_len=8, line_score=0.463, ratio_lines=0.286, final_score=0.463
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.308
trace:         score_window: window_len=21, match_len=8, line_score=0.459, ratio_lines=0.276, final_score=0.459
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=22, match_len=8, line_score=0.456, ratio_lines=0.267, final_score=0.456
trace:         score_window: window_len=23, match_len=8, line_score=0.453, ratio_lines=0.258, final_score=0.453
trace:         score_window: window_len=24, match_len=8, line_score=0.450, ratio_lines=0.250, final_score=0.450
trace:         score_window: window_len=25, match_len=8, line_score=0.447, ratio_lines=0.242, final_score=0.447
trace:         score_window: window_len=26, match_len=8, line_score=0.444, ratio_lines=0.235, final_score=0.444
trace:         score_window: window_len=27, match_len=8, line_score=0.441, ratio_lines=0.229, final_score=0.441
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=28, match_len=8, line_score=0.438, ratio_lines=0.222, final_score=0.438
trace:         score_window: window_len=29, match_len=8, line_score=0.434, ratio_lines=0.216, final_score=0.434
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=30, match_len=8, line_score=0.431, ratio_lines=0.211, final_score=0.431
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=8, match_len=8, line_score=0.375, ratio_lines=0.375, final_score=0.375
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=7, match_len=8, line_score=0.400, ratio_lines=0.400, final_score=0.400
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.308
trace:         score_window: window_len=9, match_len=8, line_score=0.373, ratio_lines=0.353, final_score=0.373
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=6, match_len=8, line_score=0.429, ratio_lines=0.429, final_score=0.429
trace:         score_window: window_len=10, match_len=8, line_score=0.370, ratio_lines=0.333, final_score=0.370
trace:         score_window: window_len=5, match_len=8, line_score=0.462, ratio_lines=0.462, final_score=0.462
trace:         score_window: window_len=11, match_len=8, line_score=0.368, ratio_lines=0.316, final_score=0.368
trace:         score_window: window_len=12, match_len=8, line_score=0.366, ratio_lines=0.300, final_score=0.366
trace:         score_window: window_len=13, match_len=8, line_score=0.363, ratio_lines=0.286, final_score=0.363
trace:         score_window: window_len=14, match_len=8, line_score=0.361, ratio_lines=0.273, final_score=0.361
trace:         score_window: window_len=15, match_len=8, line_score=0.359, ratio_lines=0.261, final_score=0.359
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=16, match_len=8, line_score=0.356, ratio_lines=0.250, final_score=0.356
trace:         score_window: window_len=17, match_len=8, line_score=0.354, ratio_lines=0.240, final_score=0.354
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=18, match_len=8, line_score=0.352, ratio_lines=0.231, final_score=0.352
trace:         score_window: window_len=19, match_len=8, line_score=0.349, ratio_lines=0.222, final_score=0.349
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=20, match_len=8, line_score=0.347, ratio_lines=0.214, final_score=0.347
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.311
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.308
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.268
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.251
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.308
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.308
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
trace:         score_window: window_len=8, match_len=8, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=7, match_len=8, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=9, match_len=8, line_score=0.248, ratio_lines=0.235, final_score=0.248
trace:         score_window: window_len=6, match_len=8, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=10, match_len=8, line_score=0.247, ratio_lines=0.222, final_score=0.247
trace:         score_window: window_len=5, match_len=8, line_score=0.308, ratio_lines=0.308, final_score=0.308
trace:         score_window: window_len=11, match_len=8, line_score=0.245, ratio_lines=0.211, final_score=0.245
debug:       compute_scored_windows (parallel) complete: scored 1302 window(s). Best candidate score=0.857 at line 29 (len=6).
trace:       Top fuzzy match candidates:
trace:         - Index 28, Len 6: Score 0.857 (Ratio 0.857) | Content: ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:         - Index 27, Len 7: Score 0.800 (Ratio 0.800) | Content: ["#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:         - Index 28, Len 7: Score 0.800 (Ratio 0.800) | Content: ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:         - Index 28, Len 5: Score 0.769 (Ratio 0.769) | Content: ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>"]
trace:         - Index 29, Len 5: Score 0.769 (Ratio 0.769) | Content: ["#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:         New best score: 0.490 (ratio 0.490 [l:0.000,w:0.000]) at index 12 (window len 8)
trace:         Tie in score (0.490) and ratio (0.490). Adding candidate: index 12, len 7
trace:         Tie in score (0.490) and ratio (0.490). Adding candidate: index 12, len 9
trace:         Tie in score (0.490) and ratio (0.490). Adding candidate: index 12, len 6
trace:         New best score: 0.601 (ratio 0.601 [l:0.111,w:0.000]) at index 12 (window len 10)
trace:         New best score: 0.690 (ratio 0.690 [l:0.200,w:0.000]) at index 12 (window len 12)
trace:         Tie in score (0.690) and ratio (0.690). Adding candidate: index 13, len 12
trace:         New best score: 0.690 (ratio 0.690 [l:0.200,w:0.000]) at index 14 (window len 12)
trace:         New best score: 0.694 (ratio 0.694 [l:0.429,w:0.162]) at index 14 (window len 20)
trace:         New best score: 0.698 (ratio 0.698 [l:0.444,w:0.182]) at index 15 (window len 19)
trace:         New best score: 0.703 (ratio 0.703 [l:0.462,w:0.703]) at index 16 (window len 18)
trace:         New best score: 0.708 (ratio 0.708 [l:0.480,w:0.708]) at index 17 (window len 17)
trace:         New best score: 0.712 (ratio 0.712 [l:0.500,w:0.712]) at index 18 (window len 16)
trace:         New best score: 0.717 (ratio 0.717 [l:0.522,w:0.717]) at index 19 (window len 15)
trace:         New best score: 0.722 (ratio 0.722 [l:0.545,w:0.722]) at index 20 (window len 14)
trace:         New best score: 0.727 (ratio 0.727 [l:0.571,w:0.727]) at index 21 (window len 13)
trace:         New best score: 0.731 (ratio 0.731 [l:0.600,w:0.731]) at index 22 (window len 12)
trace:         New best score: 0.736 (ratio 0.736 [l:0.632,w:0.736]) at index 23 (window len 11)
trace:         New best score: 0.741 (ratio 0.741 [l:0.667,w:0.741]) at index 24 (window len 10)
trace:         New best score: 0.765 (ratio 0.765 [l:0.625,w:0.698]) at index 25 (window len 8)
trace:         New best score: 0.800 (ratio 0.800 [l:0.800,w:0.800]) at index 27 (window len 7)
trace:         Tie in score (0.800) and ratio (0.800). Adding candidate: index 28, len 7
trace:         New best score: 0.857 (ratio 0.857 [l:0.857,w:0.857]) at index 28 (window len 6)
debug:     Strategy 3 (Fuzzy): 97 window(s) met threshold 0.70
trace:       Top 3 passing candidates: [("0.857", 29, 6), ("0.800", 28, 7), ("0.800", 29, 7)]
debug:     Top fuzzy candidate: start line 29 (len=6, score=0.857)
trace:       Adding candidate location at line 28 (len=7, score=0.800)
trace:       Adding candidate location at line 29 (len=7, score=0.800)
trace:       Adding candidate location at line 29 (len=5, score=0.769)
trace:       Adding candidate location at line 30 (len=5, score=0.769)
trace:       Adding candidate location at line 26 (len=8, score=0.765)
trace:       Adding candidate location at line 27 (len=8, score=0.750)
trace:       Adding candidate location at line 28 (len=8, score=0.750)
trace:       Adding candidate location at line 29 (len=8, score=0.750)
trace:       Adding candidate location at line 26 (len=9, score=0.745)
trace:       Adding candidate location at line 27 (len=9, score=0.745)
trace:       Adding candidate location at line 28 (len=9, score=0.745)
trace:       Adding candidate location at line 29 (len=9, score=0.745)
trace:       Adding candidate location at line 25 (len=10, score=0.741)
trace:       Adding candidate location at line 26 (len=10, score=0.741)
trace:       Adding candidate location at line 27 (len=10, score=0.741)
trace:       Adding candidate location at line 28 (len=10, score=0.741)
trace:       Adding candidate location at line 24 (len=11, score=0.736)
trace:       Adding candidate location at line 25 (len=11, score=0.736)
trace:       Adding candidate location at line 26 (len=11, score=0.736)
trace:       Reached maximum candidate limit (20), stopping candidate collection
debug:     Strategy 3 (Fuzzy): selected 20 candidate location(s)
trace:   Pruned candidates by min_span 5: 20 -> 20 candidate(s)
trace: DefaultHunkFinder::find_candidate_locations: returning 20 candidate(s)
debug:   Found 20 candidate location(s) for hunk. Testing sequentially...
trace:   Evaluating candidate 1/20 at location HunkLocation { start_index: 28, length: 6 } (match_type: Fuzzy { score: 0.8571428656578064 })
debug:   Found location HunkLocation { start_index: 28, length: 6 } with match type Fuzzy { score: 0.8571428656578064 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 29 (length 6), match_type=Fuzzy { score: 0.8571428656578064 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=28, len=6
trace:       File content in matched range (6 line(s)): ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.857
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=6)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 1/20 at HunkLocation { start_index: 28, length: 6 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 2/20 at location HunkLocation { start_index: 27, length: 7 } (match_type: Fuzzy { score: 0.800000011920929 })
debug:   Found location HunkLocation { start_index: 27, length: 7 } with match type Fuzzy { score: 0.800000011920929 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 28 (length 7), match_type=Fuzzy { score: 0.800000011920929 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=27, len=7
trace:       File content in matched range (7 line(s)): ["#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.800
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=6)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 2/20 at HunkLocation { start_index: 27, length: 7 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 3/20 at location HunkLocation { start_index: 28, length: 7 } (match_type: Fuzzy { score: 0.800000011920929 })
debug:   Found location HunkLocation { start_index: 28, length: 7 } with match type Fuzzy { score: 0.800000011920929 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 29 (length 7), match_type=Fuzzy { score: 0.800000011920929 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=28, len=7
trace:       File content in matched range (7 line(s)): ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.800
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 6..7 (len=1)
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:   find_statement_match_in_block: comparing target line 1 ('static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
debug:   Candidate 3/20 at HunkLocation { start_index: 28, length: 7 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 4/20 at location HunkLocation { start_index: 28, length: 5 } (match_type: Fuzzy { score: 0.7692307829856873 })
debug:   Found location HunkLocation { start_index: 28, length: 5 } with match type Fuzzy { score: 0.7692307829856873 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 29 (length 5), match_type=Fuzzy { score: 0.7692307829856873 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=28, len=5
trace:       File content in matched range (5 line(s)): ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.769
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 5 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:       DiffOp::Delete: 3 line(s) missing from target file (hunk old_idx=5)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 4/20 at HunkLocation { start_index: 28, length: 5 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 5/20 at location HunkLocation { start_index: 29, length: 5 } (match_type: Fuzzy { score: 0.7692307829856873 })
debug:   Found location HunkLocation { start_index: 29, length: 5 } with match type Fuzzy { score: 0.7692307829856873 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 30 (length 5), match_type=Fuzzy { score: 0.7692307829856873 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=29, len=5
trace:       File content in matched range (5 line(s)): ["#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.769
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Delete: 1 line(s) missing from target file (hunk old_idx=0)
trace:         Skipping stale context line missing in target: "#include \"nvidia-drm-fb.h\""
trace:       DiffOp::Equal: 5 line(s) aligned (hunk old_idx=1, file new_idx=0)
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=6)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 5/20 at HunkLocation { start_index: 29, length: 5 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 6/20 at location HunkLocation { start_index: 25, length: 8 } (match_type: Fuzzy { score: 0.7646276473999024 })
debug:   Found location HunkLocation { start_index: 25, length: 8 } with match type Fuzzy { score: 0.7646276473999024 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 26 (length 8), match_type=Fuzzy { score: 0.7646276473999024 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=25, len=8
trace:       File content in matched range (8 line(s)): ["", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.625
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 3 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: ''
trace:         Preserving inserted line: '#include \"nvidia-drm-priv.h\"'
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 5 line(s) aligned (hunk old_idx=0, file new_idx=3)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:       DiffOp::Delete: 3 line(s) missing from target file (hunk old_idx=5)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 6/20 at HunkLocation { start_index: 25, length: 8 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 7/20 at location HunkLocation { start_index: 26, length: 8 } (match_type: Fuzzy { score: 0.75 })
debug:   Found location HunkLocation { start_index: 26, length: 8 } with match type Fuzzy { score: 0.75 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 27 (length 8), match_type=Fuzzy { score: 0.75 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=26, len=8
trace:       File content in matched range (8 line(s)): ["#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.750
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '#include \"nvidia-drm-priv.h\"'
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=6)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 7/20 at HunkLocation { start_index: 26, length: 8 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 8/20 at location HunkLocation { start_index: 27, length: 8 } (match_type: Fuzzy { score: 0.75 })
debug:   Found location HunkLocation { start_index: 27, length: 8 } with match type Fuzzy { score: 0.75 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 28 (length 8), match_type=Fuzzy { score: 0.75 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=27, len=8
trace:       File content in matched range (8 line(s)): ["#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.750
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 7..8 (len=1)
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:   find_statement_match_in_block: comparing target line 1 ('static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
debug:   Candidate 8/20 at HunkLocation { start_index: 27, length: 8 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 9/20 at location HunkLocation { start_index: 28, length: 8 } (match_type: Fuzzy { score: 0.75 })
debug:   Found location HunkLocation { start_index: 28, length: 8 } with match type Fuzzy { score: 0.75 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 29 (length 8), match_type=Fuzzy { score: 0.75 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=28, len=8
trace:       File content in matched range (8 line(s)): ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.750
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 6..8 (len=2)
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:         1-to-1 replacement line validation [line 6]: is_removal=true, word_sim=0.000, char_sim=0.000
warning:     Fuzzy match rejected: Removal line "- " differs from target line "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)" (sim_words=0.000, sim_chars=0.000, required=0.500).
debug:   Candidate 9/20 at HunkLocation { start_index: 28, length: 8 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 10/20 at location HunkLocation { start_index: 25, length: 9 } (match_type: Fuzzy { score: 0.7453125185100362 })
debug:   Found location HunkLocation { start_index: 25, length: 9 } with match type Fuzzy { score: 0.7453125185100362 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 26 (length 9), match_type=Fuzzy { score: 0.7453125185100362 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=25, len=9
trace:       File content in matched range (9 line(s)): ["", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.706
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 3 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: ''
trace:         Preserving inserted line: '#include \"nvidia-drm-priv.h\"'
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=3)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=6)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 10/20 at HunkLocation { start_index: 25, length: 9 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 11/20 at location HunkLocation { start_index: 26, length: 9 } (match_type: Fuzzy { score: 0.7453125185100362 })
debug:   Found location HunkLocation { start_index: 26, length: 9 } with match type Fuzzy { score: 0.7453125185100362 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 27 (length 9), match_type=Fuzzy { score: 0.7453125185100362 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=26, len=9
trace:       File content in matched range (9 line(s)): ["#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.706
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '#include \"nvidia-drm-priv.h\"'
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 8..9 (len=1)
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:   find_statement_match_in_block: comparing target line 1 ('static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
debug:   Candidate 11/20 at HunkLocation { start_index: 26, length: 9 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 12/20 at location HunkLocation { start_index: 27, length: 9 } (match_type: Fuzzy { score: 0.7453125185100362 })
debug:   Found location HunkLocation { start_index: 27, length: 9 } with match type Fuzzy { score: 0.7453125185100362 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 28 (length 9), match_type=Fuzzy { score: 0.7453125185100362 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=27, len=9
trace:       File content in matched range (9 line(s)): ["#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.706
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 7..9 (len=2)
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:         1-to-1 replacement line validation [line 6]: is_removal=true, word_sim=0.000, char_sim=0.000
warning:     Fuzzy match rejected: Removal line "- " differs from target line "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)" (sim_words=0.000, sim_chars=0.000, required=0.500).
debug:   Candidate 12/20 at HunkLocation { start_index: 27, length: 9 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 13/20 at location HunkLocation { start_index: 28, length: 9 } (match_type: Fuzzy { score: 0.7453125185100362 })
debug:   Found location HunkLocation { start_index: 28, length: 9 } with match type Fuzzy { score: 0.7453125185100362 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 29 (length 9), match_type=Fuzzy { score: 0.7453125185100362 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{", "    struct nv_drm_device *nv_dev = to_nv_device(fb->dev);"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=28, len=9
trace:       File content in matched range (9 line(s)): ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{", "    struct nv_drm_device *nv_dev = to_nv_device(fb->dev);"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.706
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 6..9 (len=3)
trace:         Multi-line replacement (hunk_len=2, target_len=3). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 3 target line(s)
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:   find_statement_match_in_block: comparing target line 1 ('static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:   find_statement_match_in_block: comparing target line 2 ('{'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace: extract_primary_identifier: found definition identifier 'nv_drm_device' in 'struct nv_drm_device *nv_dev = to_nv_device(fb->dev);'
trace:   find_statement_match_in_block: comparing target line 3 ('struct nv_drm_device *nv_dev = to_nv_device(fb->dev);'): word_ratio=0.000, char_ratio=0.036, combined=0.036
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
debug:   Candidate 13/20 at HunkLocation { start_index: 28, length: 9 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 14/20 at location HunkLocation { start_index: 24, length: 10 } (match_type: Fuzzy { score: 0.7406250220723452 })
debug:   Found location HunkLocation { start_index: 24, length: 10 } with match type Fuzzy { score: 0.7406250220723452 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 25 (length 10), match_type=Fuzzy { score: 0.7406250220723452 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)", "", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=24, len=10
trace:       File content in matched range (10 line(s)): ["#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)", "", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.667
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 4 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)'
trace:         Preserving inserted line: ''
trace:         Preserving inserted line: '#include \"nvidia-drm-priv.h\"'
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=4)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=6)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 14/20 at HunkLocation { start_index: 24, length: 10 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 15/20 at location HunkLocation { start_index: 25, length: 10 } (match_type: Fuzzy { score: 0.7406250220723452 })
debug:   Found location HunkLocation { start_index: 25, length: 10 } with match type Fuzzy { score: 0.7406250220723452 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 26 (length 10), match_type=Fuzzy { score: 0.7406250220723452 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=25, len=10
trace:       File content in matched range (10 line(s)): ["", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.667
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 3 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: ''
trace:         Preserving inserted line: '#include \"nvidia-drm-priv.h\"'
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=3)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 9..10 (len=1)
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:   find_statement_match_in_block: comparing target line 1 ('static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
debug:   Candidate 15/20 at HunkLocation { start_index: 25, length: 10 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 16/20 at location HunkLocation { start_index: 26, length: 10 } (match_type: Fuzzy { score: 0.7406250220723452 })
debug:   Found location HunkLocation { start_index: 26, length: 10 } with match type Fuzzy { score: 0.7406250220723452 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 27 (length 10), match_type=Fuzzy { score: 0.7406250220723452 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=26, len=10
trace:       File content in matched range (10 line(s)): ["#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.667
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '#include \"nvidia-drm-priv.h\"'
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 8..10 (len=2)
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:         1-to-1 replacement line validation [line 6]: is_removal=true, word_sim=0.000, char_sim=0.000
warning:     Fuzzy match rejected: Removal line "- " differs from target line "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)" (sim_words=0.000, sim_chars=0.000, required=0.500).
debug:   Candidate 16/20 at HunkLocation { start_index: 26, length: 10 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 17/20 at location HunkLocation { start_index: 27, length: 10 } (match_type: Fuzzy { score: 0.7406250220723452 })
debug:   Found location HunkLocation { start_index: 27, length: 10 } with match type Fuzzy { score: 0.7406250220723452 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 28 (length 10), match_type=Fuzzy { score: 0.7406250220723452 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{", "    struct nv_drm_device *nv_dev = to_nv_device(fb->dev);"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=27, len=10
trace:       File content in matched range (10 line(s)): ["#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{", "    struct nv_drm_device *nv_dev = to_nv_device(fb->dev);"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.667
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 7..10 (len=3)
trace:         Multi-line replacement (hunk_len=2, target_len=3). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 3 target line(s)
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:   find_statement_match_in_block: comparing target line 1 ('static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:   find_statement_match_in_block: comparing target line 2 ('{'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace: extract_primary_identifier: found definition identifier 'nv_drm_device' in 'struct nv_drm_device *nv_dev = to_nv_device(fb->dev);'
trace:   find_statement_match_in_block: comparing target line 3 ('struct nv_drm_device *nv_dev = to_nv_device(fb->dev);'): word_ratio=0.000, char_ratio=0.036, combined=0.036
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
debug:   Candidate 17/20 at HunkLocation { start_index: 27, length: 10 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 18/20 at location HunkLocation { start_index: 23, length: 11 } (match_type: Fuzzy { score: 0.7359374707564712 })
debug:   Found location HunkLocation { start_index: 23, length: 11 } with match type Fuzzy { score: 0.7359374707564712 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 24 (length 11), match_type=Fuzzy { score: 0.7359374707564712 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["", "#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)", "", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=23, len=11
trace:       File content in matched range (11 line(s)): ["", "#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)", "", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.632
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 5 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: ''
trace:         Preserving inserted line: '#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)'
trace:         Preserving inserted line: ''
trace:         Preserving inserted line: '#include \"nvidia-drm-priv.h\"'
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=5)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=6)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 18/20 at HunkLocation { start_index: 23, length: 11 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 19/20 at location HunkLocation { start_index: 24, length: 11 } (match_type: Fuzzy { score: 0.7359374707564712 })
debug:   Found location HunkLocation { start_index: 24, length: 11 } with match type Fuzzy { score: 0.7359374707564712 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 25 (length 11), match_type=Fuzzy { score: 0.7359374707564712 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)", "", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=24, len=11
trace:       File content in matched range (11 line(s)): ["#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)", "", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.632
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 4 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)'
trace:         Preserving inserted line: ''
trace:         Preserving inserted line: '#include \"nvidia-drm-priv.h\"'
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=4)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 10..11 (len=1)
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:   find_statement_match_in_block: comparing target line 1 ('static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
debug:   Candidate 19/20 at HunkLocation { start_index: 24, length: 11 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 20/20 at location HunkLocation { start_index: 25, length: 11 } (match_type: Fuzzy { score: 0.7359374707564712 })
debug:   Found location HunkLocation { start_index: 25, length: 11 } with match type Fuzzy { score: 0.7359374707564712 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 26 (length 11), match_type=Fuzzy { score: 0.7359374707564712 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=25, len=11
trace:       File content in matched range (11 line(s)): ["", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.632
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 3 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: ''
trace:         Preserving inserted line: '#include \"nvidia-drm-priv.h\"'
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=3)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 9..11 (len=2)
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:         1-to-1 replacement line validation [line 6]: is_removal=true, word_sim=0.000, char_sim=0.000
warning:     Fuzzy match rejected: Removal line "- " differs from target line "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)" (sim_words=0.000, sim_chars=0.000, required=0.500).
debug:   Candidate 20/20 at HunkLocation { start_index: 25, length: 11 } failed with ContextNotFound. Backtracking...
debug:   Strict application failed for all 20 candidate(s). Retrying with fallback context reconciliation...
trace:   Evaluating candidate 1/20 with lenient reconciliation at location HunkLocation { start_index: 28, length: 6 }
debug:   Found location HunkLocation { start_index: 28, length: 6 } with match type Fuzzy { score: 0.8571428656578064 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 29 (length 6), match_type=Fuzzy { score: 0.8571428656578064 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=28, len=6
trace:       File content in matched range (6 line(s)): ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.857
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=6)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 2/20 with lenient reconciliation at location HunkLocation { start_index: 27, length: 7 }
debug:   Found location HunkLocation { start_index: 27, length: 7 } with match type Fuzzy { score: 0.800000011920929 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 28 (length 7), match_type=Fuzzy { score: 0.800000011920929 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=27, len=7
trace:       File content in matched range (7 line(s)): ["#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '#include "nvidia-drm-ioctl.h"' -> '#include "nvidia-drm-ioctl.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.800
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=6)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 3/20 with lenient reconciliation at location HunkLocation { start_index: 28, length: 7 }
debug:   Found location HunkLocation { start_index: 28, length: 7 } with match type Fuzzy { score: 0.800000011920929 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 29 (length 7), match_type=Fuzzy { score: 0.800000011920929 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=28, len=7
trace:       File content in matched range (7 line(s)): ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)' -> 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.800
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 6..7 (len=1)
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:   find_statement_match_in_block: comparing target line 1 ('static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
trace:   Evaluating candidate 4/20 with lenient reconciliation at location HunkLocation { start_index: 28, length: 5 }
debug:   Found location HunkLocation { start_index: 28, length: 5 } with match type Fuzzy { score: 0.7692307829856873 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 29 (length 5), match_type=Fuzzy { score: 0.7692307829856873 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=28, len=5
trace:       File content in matched range (5 line(s)): ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.769
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 5 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:       DiffOp::Delete: 3 line(s) missing from target file (hunk old_idx=5)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 5/20 with lenient reconciliation at location HunkLocation { start_index: 29, length: 5 }
debug:   Found location HunkLocation { start_index: 29, length: 5 } with match type Fuzzy { score: 0.7692307829856873 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 30 (length 5), match_type=Fuzzy { score: 0.7692307829856873 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=29, len=5
trace:       File content in matched range (5 line(s)): ["#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.769
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Delete: 1 line(s) missing from target file (hunk old_idx=0)
trace:         Skipping stale context line missing in target: "#include \"nvidia-drm-fb.h\""
trace:       DiffOp::Equal: 5 line(s) aligned (hunk old_idx=1, file new_idx=0)
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=6)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 6/20 with lenient reconciliation at location HunkLocation { start_index: 25, length: 8 }
debug:   Found location HunkLocation { start_index: 25, length: 8 } with match type Fuzzy { score: 0.7646276473999024 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 26 (length 8), match_type=Fuzzy { score: 0.7646276473999024 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=25, len=8
trace:       File content in matched range (8 line(s)): ["", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include "nvidia-drm-priv.h"' -> '#include "nvidia-drm-priv.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-ioctl.h"' -> '#include "nvidia-drm-ioctl.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.625
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 3 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: ''
trace:         Preserving inserted line: '#include \"nvidia-drm-priv.h\"'
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 5 line(s) aligned (hunk old_idx=0, file new_idx=3)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:       DiffOp::Delete: 3 line(s) missing from target file (hunk old_idx=5)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 7/20 with lenient reconciliation at location HunkLocation { start_index: 26, length: 8 }
debug:   Found location HunkLocation { start_index: 26, length: 8 } with match type Fuzzy { score: 0.75 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 27 (length 8), match_type=Fuzzy { score: 0.75 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=26, len=8
trace:       File content in matched range (8 line(s)): ["#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '#include "nvidia-drm-priv.h"' -> '#include "nvidia-drm-priv.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-ioctl.h"' -> '#include "nvidia-drm-ioctl.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.750
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '#include \"nvidia-drm-priv.h\"'
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=6)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 8/20 with lenient reconciliation at location HunkLocation { start_index: 27, length: 8 }
debug:   Found location HunkLocation { start_index: 27, length: 8 } with match type Fuzzy { score: 0.75 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 28 (length 8), match_type=Fuzzy { score: 0.75 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=27, len=8
trace:       File content in matched range (8 line(s)): ["#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '#include "nvidia-drm-ioctl.h"' -> '#include "nvidia-drm-ioctl.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)' -> 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.750
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 7..8 (len=1)
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:   find_statement_match_in_block: comparing target line 1 ('static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
trace:   Evaluating candidate 9/20 with lenient reconciliation at location HunkLocation { start_index: 28, length: 8 }
debug:   Found location HunkLocation { start_index: 28, length: 8 } with match type Fuzzy { score: 0.75 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 29 (length 8), match_type=Fuzzy { score: 0.75 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=28, len=8
trace:       File content in matched range (8 line(s)): ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)' -> 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace: normalize_line_delimiters: '{' -> '{'
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.750
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 6..8 (len=2)
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:         1-to-1 replacement line validation [line 6]: is_removal=true, word_sim=0.000, char_sim=0.000
trace: normalize_line_delimiters: '-' -> '-'
trace: normalize_line_delimiters: 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)' -> 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
warning:     Fuzzy match rejected: Removal line "- " differs from target line "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)" (sim_words=0.000, sim_chars=0.000, required=0.350).
trace:   Evaluating candidate 10/20 with lenient reconciliation at location HunkLocation { start_index: 25, length: 9 }
debug:   Found location HunkLocation { start_index: 25, length: 9 } with match type Fuzzy { score: 0.7453125185100362 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 26 (length 9), match_type=Fuzzy { score: 0.7453125185100362 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=25, len=9
trace:       File content in matched range (9 line(s)): ["", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include "nvidia-drm-priv.h"' -> '#include "nvidia-drm-priv.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-ioctl.h"' -> '#include "nvidia-drm-ioctl.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.706
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 3 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: ''
trace:         Preserving inserted line: '#include \"nvidia-drm-priv.h\"'
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=3)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=6)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 11/20 with lenient reconciliation at location HunkLocation { start_index: 26, length: 9 }
debug:   Found location HunkLocation { start_index: 26, length: 9 } with match type Fuzzy { score: 0.7453125185100362 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 27 (length 9), match_type=Fuzzy { score: 0.7453125185100362 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=26, len=9
trace:       File content in matched range (9 line(s)): ["#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '#include "nvidia-drm-priv.h"' -> '#include "nvidia-drm-priv.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-ioctl.h"' -> '#include "nvidia-drm-ioctl.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)' -> 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.706
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '#include \"nvidia-drm-priv.h\"'
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 8..9 (len=1)
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:   find_statement_match_in_block: comparing target line 1 ('static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
trace:   Evaluating candidate 12/20 with lenient reconciliation at location HunkLocation { start_index: 27, length: 9 }
debug:   Found location HunkLocation { start_index: 27, length: 9 } with match type Fuzzy { score: 0.7453125185100362 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 28 (length 9), match_type=Fuzzy { score: 0.7453125185100362 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=27, len=9
trace:       File content in matched range (9 line(s)): ["#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '#include "nvidia-drm-ioctl.h"' -> '#include "nvidia-drm-ioctl.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)' -> 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace: normalize_line_delimiters: '{' -> '{'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.706
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 7..9 (len=2)
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:         1-to-1 replacement line validation [line 6]: is_removal=true, word_sim=0.000, char_sim=0.000
trace: normalize_line_delimiters: '-' -> '-'
trace: normalize_line_delimiters: 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)' -> 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
warning:     Fuzzy match rejected: Removal line "- " differs from target line "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)" (sim_words=0.000, sim_chars=0.000, required=0.350).
trace:   Evaluating candidate 13/20 with lenient reconciliation at location HunkLocation { start_index: 28, length: 9 }
debug:   Found location HunkLocation { start_index: 28, length: 9 } with match type Fuzzy { score: 0.7453125185100362 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 29 (length 9), match_type=Fuzzy { score: 0.7453125185100362 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{", "    struct nv_drm_device *nv_dev = to_nv_device(fb->dev);"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=28, len=9
trace:       File content in matched range (9 line(s)): ["#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{", "    struct nv_drm_device *nv_dev = to_nv_device(fb->dev);"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)' -> 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace: normalize_line_delimiters: '{' -> '{'
trace: normalize_line_delimiters: '    struct nv_drm_device *nv_dev = to_nv_device(fb->dev);' -> 'struct nv_drm_device *nv_dev = to_nv_device(fb->dev)'
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.706
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 6..9 (len=3)
trace:         Multi-line replacement (hunk_len=2, target_len=3). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 3 target line(s)
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:   find_statement_match_in_block: comparing target line 1 ('static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:   find_statement_match_in_block: comparing target line 2 ('{'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace: extract_primary_identifier: found definition identifier 'nv_drm_device' in 'struct nv_drm_device *nv_dev = to_nv_device(fb->dev);'
trace:   find_statement_match_in_block: comparing target line 3 ('struct nv_drm_device *nv_dev = to_nv_device(fb->dev);'): word_ratio=0.000, char_ratio=0.036, combined=0.036
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
trace:   Evaluating candidate 14/20 with lenient reconciliation at location HunkLocation { start_index: 24, length: 10 }
debug:   Found location HunkLocation { start_index: 24, length: 10 } with match type Fuzzy { score: 0.7406250220723452 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 25 (length 10), match_type=Fuzzy { score: 0.7406250220723452 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)", "", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=24, len=10
trace:       File content in matched range (10 line(s)): ["#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)", "", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)' -> '#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include "nvidia-drm-priv.h"' -> '#include "nvidia-drm-priv.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-ioctl.h"' -> '#include "nvidia-drm-ioctl.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.667
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 4 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)'
trace:         Preserving inserted line: ''
trace:         Preserving inserted line: '#include \"nvidia-drm-priv.h\"'
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=4)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=6)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 15/20 with lenient reconciliation at location HunkLocation { start_index: 25, length: 10 }
debug:   Found location HunkLocation { start_index: 25, length: 10 } with match type Fuzzy { score: 0.7406250220723452 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 26 (length 10), match_type=Fuzzy { score: 0.7406250220723452 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=25, len=10
trace:       File content in matched range (10 line(s)): ["", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include "nvidia-drm-priv.h"' -> '#include "nvidia-drm-priv.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-ioctl.h"' -> '#include "nvidia-drm-ioctl.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)' -> 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.667
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 3 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: ''
trace:         Preserving inserted line: '#include \"nvidia-drm-priv.h\"'
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=3)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 9..10 (len=1)
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:   find_statement_match_in_block: comparing target line 1 ('static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
trace:   Evaluating candidate 16/20 with lenient reconciliation at location HunkLocation { start_index: 26, length: 10 }
debug:   Found location HunkLocation { start_index: 26, length: 10 } with match type Fuzzy { score: 0.7406250220723452 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 27 (length 10), match_type=Fuzzy { score: 0.7406250220723452 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=26, len=10
trace:       File content in matched range (10 line(s)): ["#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '#include "nvidia-drm-priv.h"' -> '#include "nvidia-drm-priv.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-ioctl.h"' -> '#include "nvidia-drm-ioctl.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)' -> 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace: normalize_line_delimiters: '{' -> '{'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.667
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '#include \"nvidia-drm-priv.h\"'
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 8..10 (len=2)
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:         1-to-1 replacement line validation [line 6]: is_removal=true, word_sim=0.000, char_sim=0.000
trace: normalize_line_delimiters: '-' -> '-'
trace: normalize_line_delimiters: 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)' -> 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
warning:     Fuzzy match rejected: Removal line "- " differs from target line "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)" (sim_words=0.000, sim_chars=0.000, required=0.350).
trace:   Evaluating candidate 17/20 with lenient reconciliation at location HunkLocation { start_index: 27, length: 10 }
debug:   Found location HunkLocation { start_index: 27, length: 10 } with match type Fuzzy { score: 0.7406250220723452 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 28 (length 10), match_type=Fuzzy { score: 0.7406250220723452 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{", "    struct nv_drm_device *nv_dev = to_nv_device(fb->dev);"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=27, len=10
trace:       File content in matched range (10 line(s)): ["#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{", "    struct nv_drm_device *nv_dev = to_nv_device(fb->dev);"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '#include "nvidia-drm-ioctl.h"' -> '#include "nvidia-drm-ioctl.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)' -> 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace: normalize_line_delimiters: '{' -> '{'
trace: normalize_line_delimiters: '    struct nv_drm_device *nv_dev = to_nv_device(fb->dev);' -> 'struct nv_drm_device *nv_dev = to_nv_device(fb->dev)'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.667
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 7..10 (len=3)
trace:         Multi-line replacement (hunk_len=2, target_len=3). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 3 target line(s)
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:   find_statement_match_in_block: comparing target line 1 ('static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:   find_statement_match_in_block: comparing target line 2 ('{'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace: extract_primary_identifier: found definition identifier 'nv_drm_device' in 'struct nv_drm_device *nv_dev = to_nv_device(fb->dev);'
trace:   find_statement_match_in_block: comparing target line 3 ('struct nv_drm_device *nv_dev = to_nv_device(fb->dev);'): word_ratio=0.000, char_ratio=0.036, combined=0.036
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
trace:   Evaluating candidate 18/20 with lenient reconciliation at location HunkLocation { start_index: 23, length: 11 }
debug:   Found location HunkLocation { start_index: 23, length: 11 } with match type Fuzzy { score: 0.7359374707564712 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 24 (length 11), match_type=Fuzzy { score: 0.7359374707564712 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["", "#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)", "", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=23, len=11
trace:       File content in matched range (11 line(s)): ["", "#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)", "", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", ""]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)' -> '#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include "nvidia-drm-priv.h"' -> '#include "nvidia-drm-priv.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-ioctl.h"' -> '#include "nvidia-drm-ioctl.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.632
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 5 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: ''
trace:         Preserving inserted line: '#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)'
trace:         Preserving inserted line: ''
trace:         Preserving inserted line: '#include \"nvidia-drm-priv.h\"'
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=5)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=6)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 19/20 with lenient reconciliation at location HunkLocation { start_index: 24, length: 11 }
debug:   Found location HunkLocation { start_index: 24, length: 11 } with match type Fuzzy { score: 0.7359374707564712 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 25 (length 11), match_type=Fuzzy { score: 0.7359374707564712 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)", "", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=24, len=11
trace:       File content in matched range (11 line(s)): ["#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)", "", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)' -> '#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include "nvidia-drm-priv.h"' -> '#include "nvidia-drm-priv.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-ioctl.h"' -> '#include "nvidia-drm-ioctl.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)' -> 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.632
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 4 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '#if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)'
trace:         Preserving inserted line: ''
trace:         Preserving inserted line: '#include \"nvidia-drm-priv.h\"'
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=4)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 10..11 (len=1)
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:   find_statement_match_in_block: comparing target line 1 ('static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
trace:   Evaluating candidate 20/20 with lenient reconciliation at location HunkLocation { start_index: 25, length: 11 }
debug:   Found location HunkLocation { start_index: 25, length: 11 } with match type Fuzzy { score: 0.7359374707564712 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 26 (length 11), match_type=Fuzzy { score: 0.7359374707564712 }, total target lines=203.
trace: Hunk::get_match_block: extracted 8 match line(s)
trace:     Match block lines: 8 | Total hunk lines: 9
trace:     Target slice to replace: ["", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=25, len=11
trace:       File content in matched range (11 line(s)): ["", "#include \"nvidia-drm-priv.h\"", "#include \"nvidia-drm-ioctl.h\"", "#include \"nvidia-drm-fb.h\"", "#include \"nvidia-drm-utils.h\"", "#include \"nvidia-drm-gem.h\"", "", "#include <drm/drm_crtc_helper.h>", "", "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)", "{"]
trace:       Parsed hunk: 8 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 8 match line(s)
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include "nvidia-drm-priv.h"' -> '#include "nvidia-drm-priv.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-ioctl.h"' -> '#include "nvidia-drm-ioctl.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-fb.h"' -> '#include "nvidia-drm-fb.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-utils.h"' -> '#include "nvidia-drm-utils.h"'
trace: normalize_line_delimiters: '#include "nvidia-drm-gem.h"' -> '#include "nvidia-drm-gem.h"'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '#include <drm/drm_crtc_helper.h>' -> '#include <drm/drm_crtc_helper.h>'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)' -> 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace: normalize_line_delimiters: '{' -> '{'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.632
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 3 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: ''
trace:         Preserving inserted line: '#include \"nvidia-drm-priv.h\"'
trace:         Preserving inserted line: '#include \"nvidia-drm-ioctl.h\"'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=3)
trace:         Equal: preserving target line: '#include \"nvidia-drm-fb.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-utils.h\"'
trace:         Equal: preserving target line: '#include \"nvidia-drm-gem.h\"'
trace:         Appended 1 addition(s) after line 2
trace:         Equal: applying addition: '#include \"nvidia-drm-helper.h\"'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '#include <drm/drm_crtc_helper.h>'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 6..8 (len=2) vs file lines 9..11 (len=2)
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace: extract_primary_identifier: found call identifier 'nv_drm_framebuffer_destroy' in 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
trace:         1-to-1 replacement line validation [line 6]: is_removal=true, word_sim=0.000, char_sim=0.000
trace: normalize_line_delimiters: '-' -> '-'
trace: normalize_line_delimiters: 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)' -> 'static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)'
warning:     Fuzzy match rejected: Removal line "- " differs from target line "static void nv_drm_framebuffer_destroy(struct drm_framebuffer *fb)" (sim_words=0.000, sim_chars=0.000, required=0.350).
warning:   All 20 candidate location(s) exhausted. Hunk application failed with: Context not found
debug:   HunkApplier: hunk 1 application outcome: Failed(ContextNotFound)
  Applying Hunk 1/1...
warning:   Failed to apply Hunk 1. Context not found
debug: HunkApplier::into_content: assembling final content from 203 line(s) (touched_eof=false, patch_ends_with_newline=true, original_ends_with_newline=true)
trace: HunkApplier::into_content: resulting content has 6166 bytes (203 lines, ends_with_newline=true)
  DRY RUN: Evaluated changes for 'nvidia-drm/nvidia-drm-fb.c' (1 hunks, clean=false)
trace:   Generating diff for dry run...
debug: apply_patches_to_dir: completed 1 patch(es). all_succeeded=true, all_applied_cleanly=false

>>> Operation 1/1
error: --- FAILED to apply patch for: nvidia-drm/nvidia-drm-fb.c
warning:   - Hunk 1 failed: Context not found
warning:     Failed Hunk Content:
warning:        #include "nvidia-drm-fb.h"
warning:        #include "nvidia-drm-utils.h"
warning:        #include "nvidia-drm-gem.h"
warning:       +#include "nvidia-drm-helper.h"
warning:        
warning:        #include <drm/drm_crtc_helper.h>
warning:        
warning:       -- 
warning:        2.20.1

--- Summary ---
Successful operations: 0
Failed operations:     1
DRY RUN completed. No files were modified.
warning: Review the log for errors. Some files may be in a partially patched state.
````

## Final Target File(s)

> This section shows the state of the target files *after* the patch operation was attempted.

*Final file state is the same as the original state because `--dry-run` was active.*

## Discrepancy Check

> This section verifies that applying the patch and then creating a new diff from the result reproduces the original input patch. This is a key integrity check.

*Discrepancy check was skipped because `--dry-run` was active.*
