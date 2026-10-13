# Mpatch Debug Report

> **Note:** This report has been partially anonymized. Please review for any remaining sensitive information before sharing.

- **Mpatch Version:** `1.7.0`
- **OS:** `linux`
- **Architecture:** `x86_64`
- **Timestamp (Unix):** `1791891888`

## Command Line

```sh
mpatch -vvvv --dry-run <INPUT_FILE> <TARGET_DIR>
```

## Input Patch File

````markdown
diff -Naur a/common/inc/nv-linux.h b/common/inc/nv-linux.h
--- a/common/inc/nv-linux.h	2026-09-30 11:52:02.204871717 +0200
+++ b/common/inc/nv-linux.h	2026-10-02 04:31:42.958813697 +0200
@@ -205,6 +205,9 @@
 #endif
 #if defined(NV_LINUX_SCREEN_INFO_H_PRESENT)
 #include <linux/screen_info.h>      /* screen_info                      */
+#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 20, 0)
+#include <linux/sysfb.h>            /* sysfb_primary_display            */
+#endif
 #else
 #include <linux/tty.h>              /* screen_info                      */
 #endif
diff -Naur a/conftest.sh b/conftest.sh
--- a/conftest.sh	2026-09-30 11:52:02.212738654 +0200
+++ b/conftest.sh	2026-10-02 04:50:42.249810823 +0200
@@ -4907,6 +4907,27 @@
             compile_check_conftest "$CODE" "NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE" "" "functions"
         ;;
 
+        is_export_symbol_present_screen_info)
+            #
+            # Determine if the export of screen_info is present.
+            #
+            # added:   2026-04-30  Archlinux AUR nvidia-390xx-utils kernel 7.0
+            #          patch that removed screen_info and replaced it with
+            #          sysfb_primary_display.
+            #
+            CODE="
+            #include <linux/types.h>
+            #include <linux/export.h>
+            #include <linux/fb.h>
+            #if defined(NV_LINUX_SCREEN_INFO_H_PRESENT)
+            #include <linux/screen_info.h>
+            #endif
+            void conftest(void) {
+                struct screen_info *si = &screen_info;
+            }"
+            compile_check_conftest "$CODE" "NV_EXPORT_SYMBOL_SCREEN_INFO" "" "symbols"
+        ;;
+
         drm_connector_has_override_edid)
             #
             # Determine if 'struct drm_connector' has an 'override_edid' member.
diff -Naur a/nvidia/nvidia.Kbuild b/nvidia/nvidia.Kbuild
--- a/nvidia/nvidia.Kbuild	2026-09-30 11:52:02.187033032 +0200
+++ b/nvidia/nvidia.Kbuild	2026-10-02 04:31:43.637811327 +0200
@@ -175,6 +175,7 @@
 NV_CONFTEST_SYMBOL_COMPILE_TESTS += is_export_symbol_gpl_of_node_to_nid
 NV_CONFTEST_SYMBOL_COMPILE_TESTS += is_export_symbol_present_swiotlb_map_sg_attrs
 NV_CONFTEST_SYMBOL_COMPILE_TESTS += is_export_symbol_present_swiotlb_dma_ops
+NV_CONFTEST_SYMBOL_COMPILE_TESTS += is_export_symbol_present_screen_info
 NV_CONFTEST_SYMBOL_COMPILE_TESTS += is_export_symbol_gpl_screen_info
 NV_CONFTEST_SYMBOL_COMPILE_TESTS += is_export_symbol_present_timer_delete_sync
 NV_CONFTEST_SYMBOL_COMPILE_TESTS += is_export_symbol_gpl___vma_start_write
diff -Naur a/nvidia/os-interface.c b/nvidia/os-interface.c
--- a/nvidia/os-interface.c	2026-09-30 11:52:02.139146055 +0200
+++ b/nvidia/os-interface.c	2026-10-02 04:31:43.638811324 +0200
@@ -1124,6 +1124,14 @@
 )
 {
 #if (defined(NVCPU_X86) || defined(NVCPU_X86_64))
+
+#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 20, 0)
+    // Rel. commit "sysfb: Replace screen_info with sysfb_primary_display" (Thomas Zimmermann, 26 Nov 2025)
+    const struct screen_info *si = &sysfb_primary_display.screen;
+#elif defined (NV_IS_EXPORT_SYMBOL_PRESENT_screen_info)
+    const struct screen_info *si = &screen_info;
+#endif
+
     //
     // If there is not a framebuffer console, return 0 size.
     //
@@ -1131,21 +1139,21 @@
     // initialization, and then will be set to a value, such as
     // VIDEO_TYPE_VLFB or VIDEO_TYPE_EFI if an fbdev console is used.
     //
-    if (screen_info.orig_video_isVGA <= 1)
+    if (si->orig_video_isVGA <= 1)
     {
         *pPhysicalAddress = 0;
         *pFbWidth = *pFbHeight = *pFbDepth = *pFbPitch = 0;
         return;
     }
 
-    *pPhysicalAddress = screen_info.lfb_base;
+    *pPhysicalAddress = si->lfb_base;
 #if defined(VIDEO_CAPABILITY_64BIT_BASE)
-    *pPhysicalAddress |= (NvU64)screen_info.ext_lfb_base << 32;
+    *pPhysicalAddress |= (NvU64)si->ext_lfb_base << 32;
 #endif
-    *pFbWidth = screen_info.lfb_width;
-    *pFbHeight = screen_info.lfb_height;
-    *pFbDepth = screen_info.lfb_depth;
-    *pFbPitch = screen_info.lfb_linelength;
+    *pFbWidth = si->lfb_width;
+    *pFbHeight = si->lfb_height;
+    *pFbDepth = si->lfb_depth;
+    *pFbPitch = si->lfb_linelength;
 #else
     *pPhysicalAddress = 0;
     *pFbWidth = *pFbHeight = *pFbDepth = *pFbPitch = 0;
diff -Naur a/nvidia-drm/nvidia-dma-fence-helper.h b/nvidia-drm/nvidia-dma-fence-helper.h
--- a/nvidia-drm/nvidia-dma-fence-helper.h	2022-10-12 11:30:31.000000000 +0200
+++ b/nvidia-drm/nvidia-dma-fence-helper.h	2026-10-02 04:31:43.095813219 +0200
@@ -89,11 +89,12 @@
 #endif
 }
 
-static inline int nv_dma_fence_signal(nv_dma_fence_t *fence) {
+// Rel. commit "dma-buf/dma-fence: Remove return code of signaling-functions" (Philipp Stanner, 1 Dec 2025)
+static inline void nv_dma_fence_signal(nv_dma_fence_t *fence) {
 #if defined(NV_LINUX_FENCE_H_PRESENT)
-    return fence_signal(fence);
+    fence_signal(fence);
 #else
-    return dma_fence_signal(fence);
+    dma_fence_signal(fence);
 #endif
 }
 

````

## Original Target File(s)

### File: `common/inc/nv-linux.h	2026-09-30 11:52:02.204871717 +0200`

*File does not exist.*
### File: `conftest.sh	2026-09-30 11:52:02.212738654 +0200`

*File does not exist.*
### File: `nvidia/nvidia.Kbuild	2026-09-30 11:52:02.187033032 +0200`

*File does not exist.*
### File: `nvidia/os-interface.c	2026-09-30 11:52:02.139146055 +0200`

*File does not exist.*
### File: `nvidia-drm/nvidia-dma-fence-helper.h	2022-10-12 11:30:31.000000000 +0200`

*File does not exist.*

## Full Trace Log

````log

Found 5 patch operation(s) to perform.
Fuzzy matching enabled with threshold: 0.70
debug: apply_patches_to_dir: applying 5 patch(es) to '.' (dry_run=true, fuzz=0.70)
debug:   [1/5] Applying patch for 'common/inc/nv-linux.h	2026-09-30 11:52:02.204871717 +0200' (1 hunk(s))
Applying patch to: common/inc/nv-linux.h	2026-09-30 11:52:02.204871717 +0200
debug:   apply_patch_to_file: target_dir='.', hunks=1, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'common/inc/nv-linux.h	2026-09-30 11:52:02.204871717 +0200'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("common")' on virtual path '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("inc")' on virtual path '<TARGET_DIR>/common'
trace:   ensure_path_is_safe: processing component 'Normal("nv-linux.h\t2026-09-30 11:52:02.204871717 +0200")' on virtual path '<TARGET_DIR>/common/inc'
trace:   Path safety verified: 'common/inc/nv-linux.h	2026-09-30 11:52:02.204871717 +0200' safely resolves to '<TARGET_DIR>/common/inc/nv-linux.h	2026-09-30 11:52:02.204871717 +0200'
debug:   Resolved safe target path: '<TARGET_DIR>/common/inc/nv-linux.h	2026-09-30 11:52:02.204871717 +0200'
trace: Hunk::get_match_block: extracted 7 match line(s)
trace: Patch::is_creation for 'common/inc/nv-linux.h	2026-09-30 11:52:02.204871717 +0200': false (first hunk old_start_line=Some(205))
debug:   Target file '<TARGET_DIR>/common/inc/nv-linux.h	2026-09-30 11:52:02.204871717 +0200' does not exist, and patch is not a creation patch. Aborting.
debug:   [2/5] Applying patch for 'conftest.sh	2026-09-30 11:52:02.212738654 +0200' (1 hunk(s))
Applying patch to: conftest.sh	2026-09-30 11:52:02.212738654 +0200
debug:   apply_patch_to_file: target_dir='.', hunks=1, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'conftest.sh	2026-09-30 11:52:02.212738654 +0200'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("conftest.sh\t2026-09-30 11:52:02.212738654 +0200")' on virtual path '<TARGET_DIR>'
trace:   Path safety verified: 'conftest.sh	2026-09-30 11:52:02.212738654 +0200' safely resolves to '<TARGET_DIR>/conftest.sh	2026-09-30 11:52:02.212738654 +0200'
debug:   Resolved safe target path: '<TARGET_DIR>/conftest.sh	2026-09-30 11:52:02.212738654 +0200'
trace: Hunk::get_match_block: extracted 7 match line(s)
trace: Patch::is_creation for 'conftest.sh	2026-09-30 11:52:02.212738654 +0200': false (first hunk old_start_line=Some(4907))
debug:   Target file '<TARGET_DIR>/conftest.sh	2026-09-30 11:52:02.212738654 +0200' does not exist, and patch is not a creation patch. Aborting.
debug:   [3/5] Applying patch for 'nvidia/nvidia.Kbuild	2026-09-30 11:52:02.187033032 +0200' (1 hunk(s))
Applying patch to: nvidia/nvidia.Kbuild	2026-09-30 11:52:02.187033032 +0200
debug:   apply_patch_to_file: target_dir='.', hunks=1, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'nvidia/nvidia.Kbuild	2026-09-30 11:52:02.187033032 +0200'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia")' on virtual path '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia.Kbuild\t2026-09-30 11:52:02.187033032 +0200")' on virtual path '<TARGET_DIR>/nvidia'
trace:   Path safety verified: 'nvidia/nvidia.Kbuild	2026-09-30 11:52:02.187033032 +0200' safely resolves to '<TARGET_DIR>/nvidia/nvidia.Kbuild	2026-09-30 11:52:02.187033032 +0200'
debug:   Resolved safe target path: '<TARGET_DIR>/nvidia/nvidia.Kbuild	2026-09-30 11:52:02.187033032 +0200'
trace: Hunk::get_match_block: extracted 7 match line(s)
trace: Patch::is_creation for 'nvidia/nvidia.Kbuild	2026-09-30 11:52:02.187033032 +0200': false (first hunk old_start_line=Some(175))
debug:   Target file '<TARGET_DIR>/nvidia/nvidia.Kbuild	2026-09-30 11:52:02.187033032 +0200' does not exist, and patch is not a creation patch. Aborting.
debug:   [4/5] Applying patch for 'nvidia/os-interface.c	2026-09-30 11:52:02.139146055 +0200' (2 hunk(s))
Applying patch to: nvidia/os-interface.c	2026-09-30 11:52:02.139146055 +0200
debug:   apply_patch_to_file: target_dir='.', hunks=2, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'nvidia/os-interface.c	2026-09-30 11:52:02.139146055 +0200'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia")' on virtual path '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("os-interface.c\t2026-09-30 11:52:02.139146055 +0200")' on virtual path '<TARGET_DIR>/nvidia'
trace:   Path safety verified: 'nvidia/os-interface.c	2026-09-30 11:52:02.139146055 +0200' safely resolves to '<TARGET_DIR>/nvidia/os-interface.c	2026-09-30 11:52:02.139146055 +0200'
debug:   Resolved safe target path: '<TARGET_DIR>/nvidia/os-interface.c	2026-09-30 11:52:02.139146055 +0200'
trace: Hunk::get_match_block: extracted 6 match line(s)
trace: Patch::is_creation for 'nvidia/os-interface.c	2026-09-30 11:52:02.139146055 +0200': false (first hunk old_start_line=Some(1124))
debug:   Target file '<TARGET_DIR>/nvidia/os-interface.c	2026-09-30 11:52:02.139146055 +0200' does not exist, and patch is not a creation patch. Aborting.
debug:   [5/5] Applying patch for 'nvidia-drm/nvidia-dma-fence-helper.h	2022-10-12 11:30:31.000000000 +0200' (1 hunk(s))
Applying patch to: nvidia-drm/nvidia-dma-fence-helper.h	2022-10-12 11:30:31.000000000 +0200
debug:   apply_patch_to_file: target_dir='.', hunks=1, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'nvidia-drm/nvidia-dma-fence-helper.h	2022-10-12 11:30:31.000000000 +0200'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-drm")' on virtual path '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-dma-fence-helper.h\t2022-10-12 11:30:31.000000000 +0200")' on virtual path '<TARGET_DIR>/nvidia-drm'
trace:   Path safety verified: 'nvidia-drm/nvidia-dma-fence-helper.h	2022-10-12 11:30:31.000000000 +0200' safely resolves to '<TARGET_DIR>/nvidia-drm/nvidia-dma-fence-helper.h	2022-10-12 11:30:31.000000000 +0200'
debug:   Resolved safe target path: '<TARGET_DIR>/nvidia-drm/nvidia-dma-fence-helper.h	2022-10-12 11:30:31.000000000 +0200'
trace: Hunk::get_match_block: extracted 10 match line(s)
trace: Patch::is_creation for 'nvidia-drm/nvidia-dma-fence-helper.h	2022-10-12 11:30:31.000000000 +0200': false (first hunk old_start_line=Some(89))
debug:   Target file '<TARGET_DIR>/nvidia-drm/nvidia-dma-fence-helper.h	2022-10-12 11:30:31.000000000 +0200' does not exist, and patch is not a creation patch. Aborting.
debug: apply_patches_to_dir: completed 5 patch(es). all_succeeded=false, all_applied_cleanly=false

>>> Operation 1/5
debug: suggest_close_file_paths: searching for candidates close to './common/inc/nv-linux.h	2026-09-30 11:52:02.204871717 +0200' in '.'
trace:   suggest_close_file_paths: descending into dir './common'
trace:   suggest_close_file_paths: descending into dir './common/inc'
trace:   suggest_close_file_paths: found candidate file 'common/inc/xapi-sdk.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nvCpuUuid.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv-kthread-q.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/uvmtypes.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv-linux.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/cpuopsys.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv-gpu-info.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nvkms-api-types.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv-memdbg.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv-register-module.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nvstatuscodes.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nvstatus.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv-timer.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv-retpoline.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv-misc.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv_uvm_interface.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nvlimits.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nvkms-kapi.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nvtypes.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv-time.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv-list-helpers.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/conftest.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv-mm.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv-kref.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv-pgprot.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nvmisc.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv-pci-types.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv_speculation_barrier.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nvgputypes.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/os-interface.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv-modeset-interface.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv-kernel-interface-api.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv-hypervisor.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nvipmi.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv-procfs.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv-lock.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv_uvm_types.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv_stdarg.h'
trace:   suggest_close_file_paths: found candidate file 'common/inc/nv-proto.h'
trace:   suggest_close_file_paths: found candidate file 'Kbuild'
trace:   suggest_close_file_paths: descending into dir './nvidia-drm'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-encoder.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-connector.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-utils.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-encoder.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-gem.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nv-pci-table.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-modeset.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-linux.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-dma-fence-helper.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-drv.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-ioctl.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-prime-fence.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-modeset.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nv-pci-table.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-priv.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-dma-resv-helper.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-fb.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-gem-user-memory.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-gem-user-memory.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-crtc.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-helper.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-gem.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm.Kbuild'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-drv.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-conftest.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-connector.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-gem-nvkms-memory.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-helper.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-utils.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-os-interface.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-fb.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-gem-nvkms-memory.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-prime-fence.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-drm/nvidia-drm-crtc.c'
trace:   suggest_close_file_paths: descending into dir './nvidia-modeset'
trace:   suggest_close_file_paths: found candidate file 'nvidia-modeset/nvidia-modeset-linux.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-modeset/nvkms.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-modeset/nvkms-ioctl.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-modeset/nvidia-modeset-os-interface.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-modeset/nvidia-modeset.Kbuild'
trace:   suggest_close_file_paths: found candidate file 'nvidia-modeset/nv-modeset-kernel.o_binary'
trace:   suggest_close_file_paths: found candidate file 'dkms.conf'
trace:   suggest_close_file_paths: found candidate file 'Makefile'
trace:   suggest_close_file_paths: descending into dir './nvidia-uvm'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_push_macros.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_perf_events.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_pmm_gpu.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_test_rng.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_gpu_access_counters.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/clc365.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm_linux_ioctl.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_range_tree_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/clc06f.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_kepler_host.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_gpu.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_va_block.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_lock.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_perf_heuristics.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/nvstatus.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_lock.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm_linux.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_maxwell.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/cla06fsubch.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_page_tree_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_perf_module.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/nvidia-uvm-sources.Kbuild'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_va_range.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_kvmalloc_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_mmu.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/clc1b5.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_pmm_sysmem.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm_linux.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_channel_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_user_channel.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_migrate.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/nvCpuUuid.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_gpu_semaphore_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_perf_module.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_gpu_isr.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_kvmalloc.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm_debug_optimized.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_volta_host.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_gpu_replayable_faults.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_mem.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/clc3b5.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_tlb_batch.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_rm_mem_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/clb0b5.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_thread_context.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/nvidia-uvm.Kbuild'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_ce_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_procfs.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm_common.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_pascal_mmu.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_pascal_fault_buffer.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_lock_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_kvmalloc.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_perf_heuristics.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_range_group_tree_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_perf_utils_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_tlb_batch.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_init.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_range_allocator.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_mem.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_thread_context.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_volta_fault_buffer.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_test_ioctl.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_perf_utils.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_volta_mmu.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_rb_tree.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_va_block.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm_minimal_init.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/clc076.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_pascal_fault_buffer.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_hal.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_range_group.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_gpu_semaphore.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_fault_buffer_flush_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_pmm_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_va_space.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_perf_prefetch.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_mmu.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/ctrl2080mc.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_volta_access_counter_buffer.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_gpu.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_gpu_isr.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm_utils.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_pte_batch.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_pmm_gpu.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_map_external.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_test_rng.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_pmm_sysmem_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_pushbuffer.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_hmm.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_tracker.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_rb_tree_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_map_external.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_forward_decl.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_rb_tree.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_hmm.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_range_allocator_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_gpu_non_replayable_faults.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_range_tree.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_gpu_replayable_faults.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_va_block_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_perf_thrashing.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_tools.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_pascal_host.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_range_tree.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_perf_events.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_get_rm_ptes_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_mmu_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_peer_identity_mappings_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_push.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_processors.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_kepler_mmu.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_range_group.h'
trace:   suggest_close_file_paths: descending into dir './nvidia-uvm/hwref'
trace:   suggest_close_file_paths: descending into dir './nvidia-uvm/hwref/volta'
trace:   suggest_close_file_paths: descending into dir './nvidia-uvm/hwref/volta/gv100'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/hwref/volta/gv100/dev_fault.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/hwref/volta/gv100/dev_fb.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/hwref/volta/gv100/dev_mmu.h'
trace:   suggest_close_file_paths: descending into dir './nvidia-uvm/hwref/pascal'
trace:   suggest_close_file_paths: descending into dir './nvidia-uvm/hwref/pascal/gp100'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/hwref/pascal/gp100/dev_fault.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/hwref/pascal/gp100/dev_fb.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/hwref/pascal/gp100/dev_master.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/hwref/pascal/gp100/dev_mmu.h'
trace:   suggest_close_file_paths: descending into dir './nvidia-uvm/hwref/kepler'
trace:   suggest_close_file_paths: descending into dir './nvidia-uvm/hwref/kepler/gk104'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/hwref/kepler/gk104/dev_mmu.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm_ioctl.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/cla0b5.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_perf_thrashing.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_hal.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_perf_utils.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_volta_fault_buffer.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/cla16f.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm_common.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_push_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_va_space.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_rm_mem.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/clb069.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_kepler.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_pascal.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/clc0b5.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_tracker_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/clb06f.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_pte_batch.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_pushbuffer.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_api.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_hal_types.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_test.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_tracker.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_global.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_tools_init.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_perf_module_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_maxwell_host.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_tools.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_range_allocator.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/clc36f.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm_unit_test.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_rm_mem.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_user_channel.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_channel.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_push.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_kepler_ce.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm_utils.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_perf_events_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_policy.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_channel.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/cla06f.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_mem_test.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_gpu_semaphore.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_pascal_ce.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_va_block_types.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_va_range.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_pmm_sysmem.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_perf_prefetch.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm_unsupported.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_volta.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_gpu_non_replayable_faults.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_global.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_gpu_access_counters.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/clc369.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia-uvm/uvm8_procfs.c'
trace:   suggest_close_file_paths: descending into dir './nvidia'
trace:   suggest_close_file_paths: found candidate file 'nvidia/os-mlock.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-p2p.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv_gpu_ops.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nvidia.Kbuild'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-pci-table.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-kthread-q-selftest.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-mempool.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-kthread-q.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-procfs.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-usermap.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/os-interface.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-dma.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-acpi.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-pat.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-report-err.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-pci-table.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-reg.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia/rmp2pdefines.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-chrdev.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-gpu-numa.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nvlink_common.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia/os-usermap.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-frontend.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-vm.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/os-registry.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-ibmnpu.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-mmap.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-memdbg.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-instance.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv_uvm_interface.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-i2c.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-gpu-numa.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia/rmil.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nvlink_linux.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nvlink_errors.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia/os-pci.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-cray.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-gvi.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nvidia-sources.Kbuild'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-p2p.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nvlink_export.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-vtophys.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-modeset-interface.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-kernel.o_binary'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-report-err.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-frontend.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-instance.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nvlink_linux.c'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-pat.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nv-ibmnpu.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nvlink_pci.h'
trace:   suggest_close_file_paths: found candidate file 'nvidia/nvlink_proto.h'
trace:   suggest_close_file_paths: found candidate file 'conftest.sh'
trace:   suggest_close_file_paths: found candidate file 'mpatch-debug-report-1791891888.md'
trace: suggest_close_file_paths: scanned 319 candidate file(s) in base directory
suggest_close_file_paths: query 'common/inc/nv-linux.h	2026-09-30 11:52:02.204871717 +0200' yielded 0 suggestion(s): []
````

## Final Target File(s)

> This section shows the state of the target files *after* the patch operation was attempted.

*Final file state is the same as the original state because `--dry-run` was active.*

## Discrepancy Check

> This section verifies that applying the patch and then creating a new diff from the result reproduces the original input patch. This is a key integrity check.

*Discrepancy check was skipped because `--dry-run` was active.*
