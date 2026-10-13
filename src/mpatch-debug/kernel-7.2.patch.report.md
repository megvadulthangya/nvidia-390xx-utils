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
diff -ruN NVIDIA-Linux-x86_64-390.157-no-compat32-patched/kernel/conftest.sh work/kernel-7.2/kernel/conftest.sh
--- a/conftest.sh	2026-10-02 21:21:30.243217501 +0200
+++ b/conftest.sh	2026-10-02 21:20:25.457855433 +0200
@@ -2345,7 +2345,7 @@
             #
             # Determine if the DRM atomic modesetting subsystem is usable
             #
-            # ("drm/atomic: Allow drivers to subclass drm_atomic_state, v3") in
+            # ("drm/atomic: Allow drivers to subclass drm_atomic_commit, v3") in
             # v4.2 (2018-05-18).
             #
             # Make conftest more robust by adding test for
@@ -3543,23 +3543,31 @@
             compile_check_conftest "$CODE" "NV_DRM_ATOMIC_MODESET_NONBLOCKING_COMMIT_AVAILABLE" "" "generic"
         ;;
 
-        drm_atomic_state_ref_counting)
+        drm_atomic_commit_ref_counting)
             #
-            # Determine if functions drm_atomic_state_get/put() are
+            # Determine if functions drm_atomic_commit_get/put() are
             # present.
             #
             # Added by commit 0853695c3ba4 ("drm: Add reference counting to
-            # drm_atomic_state") in v4.10 (2016-10-14)
+            # drm_atomic_commit") in v4.10 (2016-10-14)
             #
+
             CODE="
             #if defined(NV_DRM_DRM_ATOMIC_H_PRESENT)
             #include <drm/drm_atomic.h>
             #endif
-            void conftest_drm_atomic_state_get(void) {
-                drm_atomic_state_get();
+            #include <linux/version.h>
+
+            #if LINUX_VERSION_CODE < KERNEL_VERSION(7, 2, 0)
+            #define drm_atomic_commit_get drm_atomic_state_get
+            #define drm_atomic_commit_put drm_atomic_state_put
+            #endif
+
+            void conftest_drm_atomic_commit_get(void) {
+                drm_atomic_commit_get();
             }"
 
-            compile_check_conftest "$CODE" "NV_DRM_ATOMIC_STATE_REF_COUNTING_PRESENT" "" "functions"
+            compile_check_conftest "$CODE" "NV_DRM_ATOMIC_COMMIT_REF_COUNTING_PRESENT" "" "functions"
         ;;
 
         vm_ops_fault_removed_vma_arg)
@@ -3877,11 +3885,6 @@
             # for_each_crtc_in_state(), for_each_connector_in_state() and
             # for_each_plane_in_state() are present.
             #
-            # These old atomic state iterators were added by:
-            #   2015-04-10  df63b9994eaf942afcdb946d27a28661d7dfbf2a
-            # and they are removed by:
-            #   2017-07-19  77ac3b00b13185741effd0d5e2f1f05e4bfef7dc
-            #
             CODE="
             #include <drm/drmP.h>
             #include <drm/drm_atomic.h>
@@ -3891,13 +3894,13 @@
                 struct drm_crtc *crtc;
                 int i;
 
-                for_each_crtc_in_state(state, crtc, crtc_state, i) {
-                }
+                for_each_crtc_in_state(state, crtc, crtc_state, i) { }
             }"
 
             compile_check_conftest "$CODE" "NV_DRM_OLD_ATOMIC_STATE_ITERATORS_PRESENT" | append_conftest "types"
         ;;
 
+
         drm_mode_object_find_has_file_priv_arg)
             #
             # Determine if drm_mode_object_find() has 'file_priv' arguments.
@@ -4179,8 +4182,14 @@
             #
             CODE="
             #include <drm/drm_atomic_helper.h>
+            #include <linux/version.h>
+
+            #if LINUX_VERSION_CODE < KERNEL_VERSION(7, 2, 0)
+            #define drm_atomic_commit drm_atomic_state
+            #endif
+
             void conftest_drm_atomic_helper_swap_state_has_stall_arg(
-                    struct drm_atomic_state *state,
+                    struct drm_atomic_commit *state,
                     bool stall) {
                 (void)drm_atomic_helper_swap_state(state, stall);
             }"
@@ -4198,8 +4207,14 @@
             #
             CODE="
             #include <drm/drm_atomic_helper.h>
+            #include <linux/version.h>
+
+            #if LINUX_VERSION_CODE < KERNEL_VERSION(7, 2, 0)
+            #define drm_atomic_commit drm_atomic_state
+            #endif
+
             int conftest_drm_atomic_helper_swap_state_return_int(
-                    struct drm_atomic_state *state,
+                    struct drm_atomic_commit *state,
                     bool stall) {
                 return drm_atomic_helper_swap_state(state, stall);
             }"
@@ -4653,10 +4668,10 @@
             compile_check_conftest "$CODE" "NV_DRM_DRIVER_HAS_GEM_PRIME_CALLBACKS" "" "types"
         ;;
 
-        drm_crtc_atomic_check_has_atomic_state_arg)
+        drm_crtc_atomic_check_has_atomic_commit_arg)
             #
             # Determine if drm_crtc_helper_funcs::atomic_check takes 'state'
-            # argument of 'struct drm_atomic_state' type.
+            # argument of 'struct drm_atomic_commit' type.
             #
             # Commit 29b77ad7b9ca ("drm/atomic: Pass the full state to CRTC
             # atomic_check") in v5.11 passed the full atomic state to
@@ -4670,12 +4685,17 @@
             #
             echo "$CONFTEST_PREAMBLE
             #include <drm/drm_modeset_helper_vtables.h>
+            #include <linux/version.h>
+
+            #if LINUX_VERSION_CODE < KERNEL_VERSION(7, 2, 0)
+            #define drm_atomic_commit drm_atomic_state
+            #endif
 
             static const struct drm_crtc_helper_funcs *funcs;
-            typeof(*funcs->atomic_check) conftest_drm_crtc_atomic_check_has_atomic_state_arg;
+            typeof(*funcs->atomic_check) conftest_drm_crtc_atomic_check_has_atomic_commit_arg;
 
-            int conftest_drm_crtc_atomic_check_has_atomic_state_arg(
-                    struct drm_crtc *crtc, struct drm_atomic_state *state) {
+            int conftest_drm_crtc_atomic_check_has_atomic_commit_arg(
+                    struct drm_crtc *crtc, struct drm_atomic_commit *state) {
                 return 0;
             }" > conftest$$.c
 
@@ -4684,9 +4704,9 @@
 
             if [ -f conftest$$.o ]; then
                 rm -f conftest$$.o
-                echo "#define NV_DRM_CRTC_ATOMIC_CHECK_HAS_ATOMIC_STATE_ARG" | append_conftest "types"
+                echo "#define NV_DRM_CRTC_ATOMIC_CHECK_HAS_ATOMIC_COMMIT_ARG" | append_conftest "types"
             else
-                echo "#undef NV_DRM_CRTC_ATOMIC_CHECK_HAS_ATOMIC_STATE_ARG" | append_conftest "types"
+                echo "#undef NV_DRM_CRTC_ATOMIC_CHECK_HAS_ATOMIC_COMMIT_ARG" | append_conftest "types"
             fi
         ;;
 
@@ -4734,10 +4754,10 @@
             compile_check_conftest "$CODE" "NV_FOLLOW_PFN_PRESENT" "" "functions"
         ;;
 
-        drm_plane_atomic_check_has_atomic_state_arg)
+        drm_plane_atomic_check_has_atomic_commit_arg)
             #
             # Determine if drm_plane_helper_funcs::atomic_check takes 'state'
-            # argument of 'struct drm_atomic_state' type.
+            # argument of 'struct drm_atomic_commit' type.
             #
             # Commit 7c11b99a8e58 ("drm/atomic: Pass the full state to planes
             # atomic_check") in v5.13 passes the full atomic state to
@@ -4751,12 +4771,17 @@
             #
             echo "$CONFTEST_PREAMBLE
             #include <drm/drm_modeset_helper_vtables.h>
+            #include <linux/version.h>
+
+            #if LINUX_VERSION_CODE < KERNEL_VERSION(7, 2, 0)
+            #define drm_atomic_commit drm_atomic_state
+            #endif
 
             static const struct drm_plane_helper_funcs *funcs;
-            typeof(*funcs->atomic_check) conftest_drm_plane_atomic_check_has_atomic_state_arg;
+            typeof(*funcs->atomic_check) conftest_drm_plane_atomic_check_has_atomic_commit_arg;
 
-            int conftest_drm_plane_atomic_check_has_atomic_state_arg(
-                    struct drm_plane *plane, struct drm_atomic_state *state) {
+            int conftest_drm_plane_atomic_check_has_atomic_commit_arg(
+                    struct drm_plane *plane, struct drm_atomic_commit *state) {
                 return 0;
             }" > conftest$$.c
 
@@ -4765,9 +4790,9 @@
 
             if [ -f conftest$$.o ]; then
                 rm -f conftest$$.o
-                echo "#define NV_DRM_PLANE_ATOMIC_CHECK_HAS_ATOMIC_STATE_ARG" | append_conftest "types"
+                echo "#define NV_DRM_PLANE_ATOMIC_CHECK_HAS_ATOMIC_COMMIT_ARG" | append_conftest "types"
             else
-                echo "#undef NV_DRM_PLANE_ATOMIC_CHECK_HAS_ATOMIC_STATE_ARG" | append_conftest "types"
+                echo "#undef NV_DRM_PLANE_ATOMIC_CHECK_HAS_ATOMIC_COMMIT_ARG" | append_conftest "types"
             fi
         ;;
 
diff -ruN NVIDIA-Linux-x86_64-390.157-no-compat32-patched/kernel/nvidia/nv-gpu-numa.c work/kernel-7.2/kernel/nvidia/nv-gpu-numa.c
--- a/nvidia/nv-gpu-numa.c	2026-10-02 21:21:30.082549791 +0200
+++ b/nvidia/nv-gpu-numa.c	2026-10-02 21:20:25.461072331 +0200
@@ -158,8 +158,7 @@
     if (name_len + 1 > BUF_SIZE)
         return -ERANGE;
 
-    strncpy(name_copy, name, name_len);
-    *(name_copy + name_len) = '\0';
+    strscpy(name_copy, name, name_len + 1);
 
     // Convert the memory block ID into an integer
     if (kstrtoull(name_copy + strlen(MEMBLOCK_PREFIX), 0, &memblock_id) != 0) 
diff -ruN NVIDIA-Linux-x86_64-390.157-no-compat32-patched/kernel/nvidia/os-interface.c work/kernel-7.2/kernel/nvidia/os-interface.c
--- a/nvidia/os-interface.c	2026-10-02 21:21:30.246712089 +0200
+++ b/nvidia/os-interface.c	2026-10-02 21:20:25.462215427 +0200
@@ -640,8 +640,7 @@
 void NV_API_CALL os_get_current_process_name(char *buf, NvU32 len)
 {
     task_lock(current);
-    strncpy(buf, current->comm, len - 1);
-    buf[len - 1] = '\0';
+    strscpy(buf, current->comm, len);
     task_unlock(current);
 }
 
diff -ruN NVIDIA-Linux-x86_64-390.157-no-compat32-patched/kernel/nvidia-drm/nvidia-drm-crtc.c work/kernel-7.2/kernel/nvidia-drm/nvidia-drm-crtc.c
--- a/nvidia-drm/nvidia-drm-crtc.c	2026-10-02 21:21:30.201186837 +0200
+++ b/nvidia-drm/nvidia-drm-crtc.c	2026-10-02 21:20:25.463563716 +0200
@@ -130,15 +130,15 @@
         old_config.dstHeight != req_config->config.dstHeight;
 }
 
-#if defined(NV_DRM_PLANE_ATOMIC_CHECK_HAS_ATOMIC_STATE_ARG)
+#if defined(NV_DRM_PLANE_ATOMIC_CHECK_HAS_ATOMIC_COMMIT_ARG)
 static int nv_drm_plane_atomic_check(struct drm_plane *plane,
-                                     struct drm_atomic_state *state)
+                                     struct drm_atomic_commit *state)
 #else
 static int nv_drm_plane_atomic_check(struct drm_plane *plane,
                                      struct drm_plane_state *plane_state)
 #endif
 {
-#if defined(NV_DRM_PLANE_ATOMIC_CHECK_HAS_ATOMIC_STATE_ARG)
+#if defined(NV_DRM_PLANE_ATOMIC_CHECK_HAS_ATOMIC_COMMIT_ARG)
     struct drm_plane_state *plane_state =
         drm_atomic_get_new_plane_state(state, plane);
 #endif
@@ -333,15 +333,15 @@
  * the 'nv_drm_crtc_state::req_config', that is fine becase 'nv_drm_crtc_state'
  * will be discarded if ->atomic_check() fails.
  */
-#if defined(NV_DRM_CRTC_ATOMIC_CHECK_HAS_ATOMIC_STATE_ARG)
+#if defined(NV_DRM_CRTC_ATOMIC_CHECK_HAS_ATOMIC_COMMIT_ARG)
 static int nv_drm_crtc_atomic_check(struct drm_crtc *crtc,
-                                    struct drm_atomic_state *state)
+                                    struct drm_atomic_commit *state)
 #else
 static int nv_drm_crtc_atomic_check(struct drm_crtc *crtc,
                                     struct drm_crtc_state *crtc_state)
 #endif
 {
-#if defined(NV_DRM_CRTC_ATOMIC_CHECK_HAS_ATOMIC_STATE_ARG)
+#if defined(NV_DRM_CRTC_ATOMIC_CHECK_HAS_ATOMIC_COMMIT_ARG)
     struct drm_crtc_state *crtc_state =
         drm_atomic_get_new_crtc_state(state, crtc);
 #endif
diff -ruN NVIDIA-Linux-x86_64-390.157-no-compat32-patched/kernel/nvidia-drm/nvidia-drm-helper.c work/kernel-7.2/kernel/nvidia-drm/nvidia-drm-helper.c
--- a/nvidia-drm/nvidia-drm-helper.c	2026-10-02 21:21:30.195261766 +0200
+++ b/nvidia-drm/nvidia-drm-helper.c	2026-10-03 01:07:26.343244155 +0200
@@ -27,6 +27,23 @@
  * present simplifies nvidia-drm.ko source.
  */
 
+#include <linux/version.h>
+
+/*
+ * 7.2 renamed struct drm_atomic_state to struct drm_atomic_commit and
+ * the associated helpers. Map the old names to the new ones so the rest
+ * of this file stays unchanged across kernel versions.
+ */
+#if LINUX_VERSION_CODE >= KERNEL_VERSION(7, 2, 0)
+#define drm_atomic_state                 drm_atomic_commit
+#define drm_atomic_state_alloc           drm_atomic_commit_alloc
+#define drm_atomic_state_init            drm_atomic_commit_init
+#define drm_atomic_state_free            drm_atomic_commit_free
+#define drm_atomic_state_get             drm_atomic_commit_get
+#define drm_atomic_state_put             drm_atomic_commit_put
+#define drm_atomic_state_default_clear   drm_atomic_commit_default_clear
+#define drm_atomic_state_default_release drm_atomic_commit_default_release
+#endif
 #include "nvidia-drm-helper.h"
 
 #if defined(NV_DRM_ATOMIC_MODESET_AVAILABLE)
@@ -180,23 +197,8 @@
        }
     }
 
-#if defined(NV_DRM_ATOMIC_STATE_REF_COUNTING_PRESENT)
     drm_atomic_state_put(state);
-#else
-    if (ret != 0) {
-        drm_atomic_state_free(state);
-    } else {
-        /*
-         * In case of success, drm_atomic_commit() takes care to cleanup and
-         * free @state.
-         *
-         * Comment placed above drm_atomic_commit() says: The caller must not
-         * free or in any other way access @state. If the function fails then
-         * the caller must clean up @state itself.
-         */
-    }
-#endif
     return ret;
 }
 
-#endif /* NV_DRM_ATOMIC_MODESET_AVAILABLE */
+#endif /* NV_DRM_ATOMIC_MODESET_AVAILABLE */
\ No newline at end of file
diff -ruN NVIDIA-Linux-x86_64-390.157-no-compat32-patched/kernel/nvidia-drm/nvidia-drm.Kbuild work/kernel-7.2/kernel/nvidia-drm/nvidia-drm.Kbuild
--- a/nvidia-drm/nvidia-drm.Kbuild	2026-10-02 21:21:30.164130840 +0200
+++ b/nvidia-drm/nvidia-drm.Kbuild	2026-10-02 21:20:25.464399789 +0200
@@ -59,7 +59,7 @@
 NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_user_pages_remote
 NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_user_pages
 NV_CONFTEST_FUNCTION_COMPILE_TESTS += drm_gem_object_lookup
-NV_CONFTEST_FUNCTION_COMPILE_TESTS += drm_atomic_state_ref_counting
+NV_CONFTEST_FUNCTION_COMPILE_TESTS += drm_atomic_commit_ref_counting
 NV_CONFTEST_FUNCTION_COMPILE_TESTS += drm_driver_has_gem_prime_res_obj
 NV_CONFTEST_FUNCTION_COMPILE_TESTS += drm_atomic_helper_connector_dpms
 NV_CONFTEST_FUNCTION_COMPILE_TESTS += drm_connector_funcs_have_mode_in_name
@@ -101,9 +101,9 @@
 NV_CONFTEST_TYPE_COMPILE_TESTS += drm_driver_has_gem_free_object
 NV_CONFTEST_TYPE_COMPILE_TESTS += drm_prime_pages_to_sg_has_drm_device_arg
 NV_CONFTEST_TYPE_COMPILE_TESTS += drm_driver_has_gem_prime_callbacks
-NV_CONFTEST_TYPE_COMPILE_TESTS += drm_crtc_atomic_check_has_atomic_state_arg
+NV_CONFTEST_TYPE_COMPILE_TESTS += drm_crtc_atomic_check_has_atomic_commit_arg
 NV_CONFTEST_TYPE_COMPILE_TESTS += drm_gem_object_vmap_has_map_arg
-NV_CONFTEST_TYPE_COMPILE_TESTS += drm_plane_atomic_check_has_atomic_state_arg
+NV_CONFTEST_TYPE_COMPILE_TESTS += drm_plane_atomic_check_has_atomic_commit_arg
 NV_CONFTEST_TYPE_COMPILE_TESTS += drm_device_has_pdev
 NV_CONFTEST_TYPE_COMPILE_TESTS += dma_resv_add_fence
 NV_CONFTEST_TYPE_COMPILE_TESTS += dma_resv_reserve_fences
diff -ruN NVIDIA-Linux-x86_64-390.157-no-compat32-patched/kernel/nvidia-drm/nvidia-drm-modeset.c work/kernel-7.2/kernel/nvidia-drm/nvidia-drm-modeset.c
--- a/nvidia-drm/nvidia-drm-modeset.c	2026-10-02 21:21:30.201563632 +0200
+++ b/nvidia-drm/nvidia-drm-modeset.c	2026-10-03 00:45:27.843953694 +0200
@@ -42,23 +42,23 @@
 #include <drm/drm_atomic_helper.h>
 #include <drm/drm_crtc.h>
 
-struct nv_drm_atomic_state {
+struct nv_drm_atomic_commit {
     struct NvKmsKapiRequestedModeSetConfig config;
-    struct drm_atomic_state base;
+    struct drm_atomic_commit base;
 };
 
-static inline struct nv_drm_atomic_state *to_nv_atomic_state(
-    struct drm_atomic_state *state)
+static inline struct nv_drm_atomic_commit *to_nv_atomic_commit(
+    struct drm_atomic_commit *state)
 {
-    return container_of(state, struct nv_drm_atomic_state, base);
+    return container_of(state, struct nv_drm_atomic_commit, base);
 }
 
-struct drm_atomic_state *nv_drm_atomic_state_alloc(struct drm_device *dev)
+struct drm_atomic_commit *nv_drm_atomic_state_alloc(struct drm_device *dev)
 {
-    struct nv_drm_atomic_state *nv_state =
+    struct nv_drm_atomic_commit *nv_state =
             nv_drm_calloc(1, sizeof(*nv_state));
 
-    if (nv_state == NULL || drm_atomic_state_init(dev, &nv_state->base) < 0) {
+    if (nv_state == NULL || drm_atomic_commit_init(dev, &nv_state->base) < 0) {
         nv_drm_free(nv_state);
         return NULL;
     }
@@ -66,16 +66,16 @@
     return &nv_state->base;
 }
 
-void nv_drm_atomic_state_clear(struct drm_atomic_state *state)
+void nv_drm_atomic_state_clear(struct drm_atomic_commit *state)
 {
-    drm_atomic_state_default_clear(state);
+    drm_atomic_commit_default_clear(state);
 }
 
-void nv_drm_atomic_state_free(struct drm_atomic_state *state)
+void nv_drm_atomic_state_free(struct drm_atomic_commit *state)
 {
-    struct nv_drm_atomic_state *nv_state =
-                    to_nv_atomic_state(state);
-    drm_atomic_state_default_release(state);
+    struct nv_drm_atomic_commit *nv_state =
+                    to_nv_atomic_commit(state);
+    drm_atomic_commit_default_release(state);
     nv_drm_free(nv_state);
 }
 
@@ -105,12 +105,12 @@
  */
 static int
 nv_drm_atomic_apply_modeset_config(struct drm_device *dev,
-                                   struct drm_atomic_state *state,
+                                   struct drm_atomic_commit *state,
                                    bool commit)
 {
     struct nv_drm_device *nv_dev = to_nv_device(dev);
     struct NvKmsKapiRequestedModeSetConfig *requested_config =
-        &(to_nv_atomic_state(state)->config);
+        &(to_nv_atomic_commit(state)->config);
     struct drm_crtc *crtc;
     struct drm_crtc_state *old_crtc_state, *new_crtc_state;
     int i;
@@ -161,7 +161,7 @@
 }
 
 int nv_drm_atomic_check(struct drm_device *dev,
-                        struct drm_atomic_state *state)
+                        struct drm_atomic_commit *state)
 {
     int ret = 0;
 
@@ -205,7 +205,7 @@
 }
 
 int nv_drm_atomic_commit(struct drm_device *dev,
-                         struct drm_atomic_state *state,
+                         struct drm_atomic_commit *state,
                          bool nonblock)
 {
     int ret = -EBUSY;
@@ -333,13 +333,13 @@
         }
     }
 
-#if defined(NV_DRM_ATOMIC_STATE_REF_COUNTING_PRESENT)
+#if LINUX_VERSION_CODE >= KERNEL_VERSION(7, 2, 0)
     /*
-     * If ref counting is present, state will be freed when the caller
-     * drops its reference after we return.
+     * 7.2+: state will be freed when the caller drops its reference
+     * after we return.
      */
 #else
-    drm_atomic_state_free(state);
+    drm_atomic_commit_put(state);
 #endif
 
     return 0;
diff -ruN NVIDIA-Linux-x86_64-390.157-no-compat32-patched/kernel/nvidia-drm/nvidia-drm-modeset.h work/kernel-7.2/kernel/nvidia-drm/nvidia-drm-modeset.h
--- a/nvidia-drm/nvidia-drm-modeset.h	2022-10-12 11:30:31.000000000 +0200
+++ b/nvidia-drm/nvidia-drm-modeset.h	2026-10-02 21:20:25.465716929 +0200
@@ -30,17 +30,17 @@
 #include "nvkms-kapi.h"
 
 struct drm_device;
-struct drm_atomic_state;
+struct drm_atomic_commit;
 
-struct drm_atomic_state *nv_drm_atomic_state_alloc(struct drm_device *dev);
-void nv_drm_atomic_state_clear(struct drm_atomic_state *state);
-void nv_drm_atomic_state_free(struct drm_atomic_state *state);
+struct drm_atomic_commit *nv_drm_atomic_state_alloc(struct drm_device *dev);
+void nv_drm_atomic_state_clear(struct drm_atomic_commit *state);
+void nv_drm_atomic_state_free(struct drm_atomic_commit *state);
 
 int nv_drm_atomic_check(struct drm_device *dev,
-                        struct drm_atomic_state *state);
+                        struct drm_atomic_commit *state);
 
 int nv_drm_atomic_commit(struct drm_device *dev,
-                         struct drm_atomic_state *state, bool nonblock);
+                         struct drm_atomic_commit *state, bool nonblock);
 
 
 void nv_drm_handle_flip_occurred(struct nv_drm_device *nv_dev,
diff -ruN NVIDIA-Linux-x86_64-390.157-no-compat32-patched/kernel/nvidia-drm/nvidia-drm-priv.h work/kernel-7.2/kernel/nvidia-drm/nvidia-drm-priv.h
--- a/nvidia-drm/nvidia-drm-priv.h	2026-10-02 21:21:30.170117581 +0200
+++ b/nvidia-drm/nvidia-drm-priv.h	2026-10-02 21:20:25.466018016 +0200
@@ -23,6 +23,19 @@
 #ifndef __NVIDIA_DRM_PRIV_H__
 #define __NVIDIA_DRM_PRIV_H__
 
+#include <linux/version.h>
+
+/* 7.2 kernel: drm_atomic_state renamed to drm_atomic_commit */
+#if LINUX_VERSION_CODE < KERNEL_VERSION(7, 2, 0)
+#define drm_atomic_commit                 drm_atomic_state
+#define drm_atomic_commit_init            drm_atomic_state_init
+#define drm_atomic_commit_free            drm_atomic_state_free
+#define drm_atomic_commit_get             drm_atomic_state_get
+#define drm_atomic_commit_put             drm_atomic_state_put
+#define drm_atomic_commit_default_clear   drm_atomic_state_default_clear
+#define drm_atomic_commit_default_release drm_atomic_state_default_release
+#endif
+
 #include "nvidia-drm-conftest.h" /* NV_DRM_AVAILABLE */
 
 #if defined(NV_DRM_AVAILABLE)
diff -ruN NVIDIA-Linux-x86_64-390.157-no-compat32-patched/kernel/nvidia-modeset/nvidia-modeset-linux.c work/kernel-7.2/kernel/nvidia-modeset/nvidia-modeset-linux.c
--- a/nvidia-modeset/nvidia-modeset-linux.c	2026-10-02 21:21:30.146064669 +0200
+++ b/nvidia-modeset/nvidia-modeset-linux.c	2026-10-02 21:20:25.466761688 +0200
@@ -20,6 +20,7 @@
 #include <linux/random.h>
 #include <linux/file.h>
 #include <linux/list.h>
+#include <linux/version.h>
 
 #include "nvstatus.h"
 
@@ -185,7 +186,16 @@
 
 char* NVKMS_API_CALL nvkms_strncpy(char *dest, const char *src, size_t n)
 {
+#if LINUX_VERSION_CODE >= KERNEL_VERSION(7, 2, 0)
+    size_t i;
+    for (i = 0; i < n && src[i] != '\0'; i++)
+        dest[i] = src[i];
+    for (; i < n; i++)
+        dest[i] = '\0';
+    return dest;
+#else
     return strncpy(dest, src, n);
+#endif
 }
 
 void NVKMS_API_CALL nvkms_usleep(NvU64 usec)
diff -ruN NVIDIA-Linux-x86_64-390.157-no-compat32-patched/kernel/nvidia-uvm/uvm8_pmm_gpu.c work/kernel-7.2/kernel/nvidia-uvm/uvm8_pmm_gpu.c
--- a/nvidia-uvm/uvm8_pmm_gpu.c	2026-10-02 21:21:30.107547239 +0200
+++ b/nvidia-uvm/uvm8_pmm_gpu.c	2026-10-02 21:20:25.468074288 +0200
@@ -2794,7 +2794,7 @@
             size_t size;
             size_t align;
             if (level == 0) {
-                strncpy(chunk_split_cache[level].name, "uvm_gpu_chunk_t", sizeof(chunk_split_cache[level].name) - 1);
+                strscpy(chunk_split_cache[level].name, "uvm_gpu_chunk_t", sizeof(chunk_split_cache[level].name));
                 size = sizeof(uvm_gpu_chunk_t);
                 align = __alignof__(uvm_gpu_chunk_t);
             } else {

````

## Original Target File(s)

### File: `conftest.sh	2026-10-02 21:21:30.243217501 +0200`

*File does not exist.*
### File: `nvidia/nv-gpu-numa.c	2026-10-02 21:21:30.082549791 +0200`

*File does not exist.*
### File: `nvidia/os-interface.c	2026-10-02 21:21:30.246712089 +0200`

*File does not exist.*
### File: `nvidia-drm/nvidia-drm-crtc.c	2026-10-02 21:21:30.201186837 +0200`

*File does not exist.*
### File: `nvidia-drm/nvidia-drm-helper.c	2026-10-02 21:21:30.195261766 +0200`

*File does not exist.*
### File: `nvidia-drm/nvidia-drm.Kbuild	2026-10-02 21:21:30.164130840 +0200`

*File does not exist.*
### File: `nvidia-drm/nvidia-drm-modeset.c	2026-10-02 21:21:30.201563632 +0200`

*File does not exist.*
### File: `nvidia-drm/nvidia-drm-modeset.h	2022-10-12 11:30:31.000000000 +0200`

*File does not exist.*
### File: `nvidia-drm/nvidia-drm-priv.h	2026-10-02 21:21:30.170117581 +0200`

*File does not exist.*
### File: `nvidia-modeset/nvidia-modeset-linux.c	2026-10-02 21:21:30.146064669 +0200`

*File does not exist.*
### File: `nvidia-uvm/uvm8_pmm_gpu.c	2026-10-02 21:21:30.107547239 +0200`

*File does not exist.*

## Full Trace Log

````log

Found 11 patch operation(s) to perform.
Fuzzy matching enabled with threshold: 0.70
debug: apply_patches_to_dir: applying 11 patch(es) to '.' (dry_run=true, fuzz=0.70)
debug:   [1/11] Applying patch for 'conftest.sh	2026-10-02 21:21:30.243217501 +0200' (12 hunk(s))
Applying patch to: conftest.sh	2026-10-02 21:21:30.243217501 +0200
debug:   apply_patch_to_file: target_dir='.', hunks=12, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'conftest.sh	2026-10-02 21:21:30.243217501 +0200'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("conftest.sh\t2026-10-02 21:21:30.243217501 +0200")' on virtual path '<TARGET_DIR>'
trace:   Path safety verified: 'conftest.sh	2026-10-02 21:21:30.243217501 +0200' safely resolves to '<TARGET_DIR>/conftest.sh	2026-10-02 21:21:30.243217501 +0200'
debug:   Resolved safe target path: '<TARGET_DIR>/conftest.sh	2026-10-02 21:21:30.243217501 +0200'
trace: Hunk::get_match_block: extracted 7 match line(s)
trace: Patch::is_creation for 'conftest.sh	2026-10-02 21:21:30.243217501 +0200': false (first hunk old_start_line=Some(2345))
debug:   Target file '<TARGET_DIR>/conftest.sh	2026-10-02 21:21:30.243217501 +0200' does not exist, and patch is not a creation patch. Aborting.
debug:   [2/11] Applying patch for 'nvidia/nv-gpu-numa.c	2026-10-02 21:21:30.082549791 +0200' (1 hunk(s))
Applying patch to: nvidia/nv-gpu-numa.c	2026-10-02 21:21:30.082549791 +0200
debug:   apply_patch_to_file: target_dir='.', hunks=1, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'nvidia/nv-gpu-numa.c	2026-10-02 21:21:30.082549791 +0200'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia")' on virtual path '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nv-gpu-numa.c\t2026-10-02 21:21:30.082549791 +0200")' on virtual path '<TARGET_DIR>/nvidia'
trace:   Path safety verified: 'nvidia/nv-gpu-numa.c	2026-10-02 21:21:30.082549791 +0200' safely resolves to '<TARGET_DIR>/nvidia/nv-gpu-numa.c	2026-10-02 21:21:30.082549791 +0200'
debug:   Resolved safe target path: '<TARGET_DIR>/nvidia/nv-gpu-numa.c	2026-10-02 21:21:30.082549791 +0200'
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: Patch::is_creation for 'nvidia/nv-gpu-numa.c	2026-10-02 21:21:30.082549791 +0200': false (first hunk old_start_line=Some(158))
debug:   Target file '<TARGET_DIR>/nvidia/nv-gpu-numa.c	2026-10-02 21:21:30.082549791 +0200' does not exist, and patch is not a creation patch. Aborting.
debug:   [3/11] Applying patch for 'nvidia/os-interface.c	2026-10-02 21:21:30.246712089 +0200' (1 hunk(s))
Applying patch to: nvidia/os-interface.c	2026-10-02 21:21:30.246712089 +0200
debug:   apply_patch_to_file: target_dir='.', hunks=1, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'nvidia/os-interface.c	2026-10-02 21:21:30.246712089 +0200'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia")' on virtual path '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("os-interface.c\t2026-10-02 21:21:30.246712089 +0200")' on virtual path '<TARGET_DIR>/nvidia'
trace:   Path safety verified: 'nvidia/os-interface.c	2026-10-02 21:21:30.246712089 +0200' safely resolves to '<TARGET_DIR>/nvidia/os-interface.c	2026-10-02 21:21:30.246712089 +0200'
debug:   Resolved safe target path: '<TARGET_DIR>/nvidia/os-interface.c	2026-10-02 21:21:30.246712089 +0200'
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: Patch::is_creation for 'nvidia/os-interface.c	2026-10-02 21:21:30.246712089 +0200': false (first hunk old_start_line=Some(640))
debug:   Target file '<TARGET_DIR>/nvidia/os-interface.c	2026-10-02 21:21:30.246712089 +0200' does not exist, and patch is not a creation patch. Aborting.
debug:   [4/11] Applying patch for 'nvidia-drm/nvidia-drm-crtc.c	2026-10-02 21:21:30.201186837 +0200' (2 hunk(s))
Applying patch to: nvidia-drm/nvidia-drm-crtc.c	2026-10-02 21:21:30.201186837 +0200
debug:   apply_patch_to_file: target_dir='.', hunks=2, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'nvidia-drm/nvidia-drm-crtc.c	2026-10-02 21:21:30.201186837 +0200'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-drm")' on virtual path '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-drm-crtc.c\t2026-10-02 21:21:30.201186837 +0200")' on virtual path '<TARGET_DIR>/nvidia-drm'
trace:   Path safety verified: 'nvidia-drm/nvidia-drm-crtc.c	2026-10-02 21:21:30.201186837 +0200' safely resolves to '<TARGET_DIR>/nvidia-drm/nvidia-drm-crtc.c	2026-10-02 21:21:30.201186837 +0200'
debug:   Resolved safe target path: '<TARGET_DIR>/nvidia-drm/nvidia-drm-crtc.c	2026-10-02 21:21:30.201186837 +0200'
trace: Hunk::get_match_block: extracted 15 match line(s)
trace: Patch::is_creation for 'nvidia-drm/nvidia-drm-crtc.c	2026-10-02 21:21:30.201186837 +0200': false (first hunk old_start_line=Some(130))
debug:   Target file '<TARGET_DIR>/nvidia-drm/nvidia-drm-crtc.c	2026-10-02 21:21:30.201186837 +0200' does not exist, and patch is not a creation patch. Aborting.
debug:   [5/11] Applying patch for 'nvidia-drm/nvidia-drm-helper.c	2026-10-02 21:21:30.195261766 +0200' (2 hunk(s))
Applying patch to: nvidia-drm/nvidia-drm-helper.c	2026-10-02 21:21:30.195261766 +0200
debug:   apply_patch_to_file: target_dir='.', hunks=2, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'nvidia-drm/nvidia-drm-helper.c	2026-10-02 21:21:30.195261766 +0200'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-drm")' on virtual path '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-drm-helper.c\t2026-10-02 21:21:30.195261766 +0200")' on virtual path '<TARGET_DIR>/nvidia-drm'
trace:   Path safety verified: 'nvidia-drm/nvidia-drm-helper.c	2026-10-02 21:21:30.195261766 +0200' safely resolves to '<TARGET_DIR>/nvidia-drm/nvidia-drm-helper.c	2026-10-02 21:21:30.195261766 +0200'
debug:   Resolved safe target path: '<TARGET_DIR>/nvidia-drm/nvidia-drm-helper.c	2026-10-02 21:21:30.195261766 +0200'
trace: Hunk::get_match_block: extracted 6 match line(s)
trace: Patch::is_creation for 'nvidia-drm/nvidia-drm-helper.c	2026-10-02 21:21:30.195261766 +0200': false (first hunk old_start_line=Some(27))
debug:   Target file '<TARGET_DIR>/nvidia-drm/nvidia-drm-helper.c	2026-10-02 21:21:30.195261766 +0200' does not exist, and patch is not a creation patch. Aborting.
debug:   [6/11] Applying patch for 'nvidia-drm/nvidia-drm.Kbuild	2026-10-02 21:21:30.164130840 +0200' (2 hunk(s))
Applying patch to: nvidia-drm/nvidia-drm.Kbuild	2026-10-02 21:21:30.164130840 +0200
debug:   apply_patch_to_file: target_dir='.', hunks=2, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'nvidia-drm/nvidia-drm.Kbuild	2026-10-02 21:21:30.164130840 +0200'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-drm")' on virtual path '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-drm.Kbuild\t2026-10-02 21:21:30.164130840 +0200")' on virtual path '<TARGET_DIR>/nvidia-drm'
trace:   Path safety verified: 'nvidia-drm/nvidia-drm.Kbuild	2026-10-02 21:21:30.164130840 +0200' safely resolves to '<TARGET_DIR>/nvidia-drm/nvidia-drm.Kbuild	2026-10-02 21:21:30.164130840 +0200'
debug:   Resolved safe target path: '<TARGET_DIR>/nvidia-drm/nvidia-drm.Kbuild	2026-10-02 21:21:30.164130840 +0200'
trace: Hunk::get_match_block: extracted 7 match line(s)
trace: Patch::is_creation for 'nvidia-drm/nvidia-drm.Kbuild	2026-10-02 21:21:30.164130840 +0200': false (first hunk old_start_line=Some(59))
debug:   Target file '<TARGET_DIR>/nvidia-drm/nvidia-drm.Kbuild	2026-10-02 21:21:30.164130840 +0200' does not exist, and patch is not a creation patch. Aborting.
debug:   [7/11] Applying patch for 'nvidia-drm/nvidia-drm-modeset.c	2026-10-02 21:21:30.201563632 +0200' (6 hunk(s))
Applying patch to: nvidia-drm/nvidia-drm-modeset.c	2026-10-02 21:21:30.201563632 +0200
debug:   apply_patch_to_file: target_dir='.', hunks=6, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'nvidia-drm/nvidia-drm-modeset.c	2026-10-02 21:21:30.201563632 +0200'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-drm")' on virtual path '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-drm-modeset.c\t2026-10-02 21:21:30.201563632 +0200")' on virtual path '<TARGET_DIR>/nvidia-drm'
trace:   Path safety verified: 'nvidia-drm/nvidia-drm-modeset.c	2026-10-02 21:21:30.201563632 +0200' safely resolves to '<TARGET_DIR>/nvidia-drm/nvidia-drm-modeset.c	2026-10-02 21:21:30.201563632 +0200'
debug:   Resolved safe target path: '<TARGET_DIR>/nvidia-drm/nvidia-drm-modeset.c	2026-10-02 21:21:30.201563632 +0200'
trace: Hunk::get_match_block: extracted 23 match line(s)
trace: Patch::is_creation for 'nvidia-drm/nvidia-drm-modeset.c	2026-10-02 21:21:30.201563632 +0200': false (first hunk old_start_line=Some(42))
debug:   Target file '<TARGET_DIR>/nvidia-drm/nvidia-drm-modeset.c	2026-10-02 21:21:30.201563632 +0200' does not exist, and patch is not a creation patch. Aborting.
debug:   [8/11] Applying patch for 'nvidia-drm/nvidia-drm-modeset.h	2022-10-12 11:30:31.000000000 +0200' (1 hunk(s))
Applying patch to: nvidia-drm/nvidia-drm-modeset.h	2022-10-12 11:30:31.000000000 +0200
debug:   apply_patch_to_file: target_dir='.', hunks=1, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'nvidia-drm/nvidia-drm-modeset.h	2022-10-12 11:30:31.000000000 +0200'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-drm")' on virtual path '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-drm-modeset.h\t2022-10-12 11:30:31.000000000 +0200")' on virtual path '<TARGET_DIR>/nvidia-drm'
trace:   Path safety verified: 'nvidia-drm/nvidia-drm-modeset.h	2022-10-12 11:30:31.000000000 +0200' safely resolves to '<TARGET_DIR>/nvidia-drm/nvidia-drm-modeset.h	2022-10-12 11:30:31.000000000 +0200'
debug:   Resolved safe target path: '<TARGET_DIR>/nvidia-drm/nvidia-drm-modeset.h	2022-10-12 11:30:31.000000000 +0200'
trace: Hunk::get_match_block: extracted 18 match line(s)
trace: Patch::is_creation for 'nvidia-drm/nvidia-drm-modeset.h	2022-10-12 11:30:31.000000000 +0200': false (first hunk old_start_line=Some(30))
debug:   Target file '<TARGET_DIR>/nvidia-drm/nvidia-drm-modeset.h	2022-10-12 11:30:31.000000000 +0200' does not exist, and patch is not a creation patch. Aborting.
debug:   [9/11] Applying patch for 'nvidia-drm/nvidia-drm-priv.h	2026-10-02 21:21:30.170117581 +0200' (1 hunk(s))
Applying patch to: nvidia-drm/nvidia-drm-priv.h	2026-10-02 21:21:30.170117581 +0200
debug:   apply_patch_to_file: target_dir='.', hunks=1, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'nvidia-drm/nvidia-drm-priv.h	2026-10-02 21:21:30.170117581 +0200'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-drm")' on virtual path '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-drm-priv.h\t2026-10-02 21:21:30.170117581 +0200")' on virtual path '<TARGET_DIR>/nvidia-drm'
trace:   Path safety verified: 'nvidia-drm/nvidia-drm-priv.h	2026-10-02 21:21:30.170117581 +0200' safely resolves to '<TARGET_DIR>/nvidia-drm/nvidia-drm-priv.h	2026-10-02 21:21:30.170117581 +0200'
debug:   Resolved safe target path: '<TARGET_DIR>/nvidia-drm/nvidia-drm-priv.h	2026-10-02 21:21:30.170117581 +0200'
trace: Hunk::get_match_block: extracted 7 match line(s)
trace: Patch::is_creation for 'nvidia-drm/nvidia-drm-priv.h	2026-10-02 21:21:30.170117581 +0200': false (first hunk old_start_line=Some(23))
debug:   Target file '<TARGET_DIR>/nvidia-drm/nvidia-drm-priv.h	2026-10-02 21:21:30.170117581 +0200' does not exist, and patch is not a creation patch. Aborting.
debug:   [10/11] Applying patch for 'nvidia-modeset/nvidia-modeset-linux.c	2026-10-02 21:21:30.146064669 +0200' (2 hunk(s))
Applying patch to: nvidia-modeset/nvidia-modeset-linux.c	2026-10-02 21:21:30.146064669 +0200
debug:   apply_patch_to_file: target_dir='.', hunks=2, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'nvidia-modeset/nvidia-modeset-linux.c	2026-10-02 21:21:30.146064669 +0200'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-modeset")' on virtual path '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-modeset-linux.c\t2026-10-02 21:21:30.146064669 +0200")' on virtual path '<TARGET_DIR>/nvidia-modeset'
trace:   Path safety verified: 'nvidia-modeset/nvidia-modeset-linux.c	2026-10-02 21:21:30.146064669 +0200' safely resolves to '<TARGET_DIR>/nvidia-modeset/nvidia-modeset-linux.c	2026-10-02 21:21:30.146064669 +0200'
debug:   Resolved safe target path: '<TARGET_DIR>/nvidia-modeset/nvidia-modeset-linux.c	2026-10-02 21:21:30.146064669 +0200'
trace: Hunk::get_match_block: extracted 5 match line(s)
trace: Patch::is_creation for 'nvidia-modeset/nvidia-modeset-linux.c	2026-10-02 21:21:30.146064669 +0200': false (first hunk old_start_line=Some(20))
debug:   Target file '<TARGET_DIR>/nvidia-modeset/nvidia-modeset-linux.c	2026-10-02 21:21:30.146064669 +0200' does not exist, and patch is not a creation patch. Aborting.
debug:   [11/11] Applying patch for 'nvidia-uvm/uvm8_pmm_gpu.c	2026-10-02 21:21:30.107547239 +0200' (1 hunk(s))
Applying patch to: nvidia-uvm/uvm8_pmm_gpu.c	2026-10-02 21:21:30.107547239 +0200
debug:   apply_patch_to_file: target_dir='.', hunks=1, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'nvidia-uvm/uvm8_pmm_gpu.c	2026-10-02 21:21:30.107547239 +0200'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-uvm")' on virtual path '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("uvm8_pmm_gpu.c\t2026-10-02 21:21:30.107547239 +0200")' on virtual path '<TARGET_DIR>/nvidia-uvm'
trace:   Path safety verified: 'nvidia-uvm/uvm8_pmm_gpu.c	2026-10-02 21:21:30.107547239 +0200' safely resolves to '<TARGET_DIR>/nvidia-uvm/uvm8_pmm_gpu.c	2026-10-02 21:21:30.107547239 +0200'
debug:   Resolved safe target path: '<TARGET_DIR>/nvidia-uvm/uvm8_pmm_gpu.c	2026-10-02 21:21:30.107547239 +0200'
trace: Hunk::get_match_block: extracted 7 match line(s)
trace: Patch::is_creation for 'nvidia-uvm/uvm8_pmm_gpu.c	2026-10-02 21:21:30.107547239 +0200': false (first hunk old_start_line=Some(2794))
debug:   Target file '<TARGET_DIR>/nvidia-uvm/uvm8_pmm_gpu.c	2026-10-02 21:21:30.107547239 +0200' does not exist, and patch is not a creation patch. Aborting.
debug: apply_patches_to_dir: completed 11 patch(es). all_succeeded=false, all_applied_cleanly=false

>>> Operation 1/11
debug: suggest_close_file_paths: searching for candidates close to './conftest.sh	2026-10-02 21:21:30.243217501 +0200' in '.'
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
suggest_close_file_paths: query 'conftest.sh	2026-10-02 21:21:30.243217501 +0200' yielded 0 suggestion(s): []
````

## Final Target File(s)

> This section shows the state of the target files *after* the patch operation was attempted.

*Final file state is the same as the original state because `--dry-run` was active.*

## Discrepancy Check

> This section verifies that applying the patch and then creating a new diff from the result reproduces the original input patch. This is a key integrity check.

*Discrepancy check was skipped because `--dry-run` was active.*
