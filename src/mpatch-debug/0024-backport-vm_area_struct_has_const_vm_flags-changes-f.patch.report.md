# Mpatch Debug Report

> **Note:** This report has been partially anonymized. Please review for any remaining sensitive information before sharing.

- **Mpatch Version:** `1.6.4`
- **OS:** `linux`
- **Architecture:** `x86_64`
- **Timestamp (Unix):** `1790784833`

## Command Line

```sh
mpatch -vvvv --dry-run <INPUT_FILE> <TARGET_DIR>
```

## Input Patch File

````markdown
From c0557d49b7076338a8fe12f1a8d68fff45a76c08 Mon Sep 17 00:00:00 2001
From: Andreas Beckmann <anbe@debian.org>
Date: Wed, 31 May 2023 12:25:55 +0200
Subject: [PATCH 2/2] backport vm_area_struct_has_const_vm_flags changes from
 525.105.17 (uvm part)

---
 nvidia-uvm/nvidia-uvm.Kbuild | 1 +
 nvidia-uvm/uvm8.c            | 2 +-
 2 files changed, 2 insertions(+), 1 deletion(-)

diff --git a/nvidia-uvm/nvidia-uvm.Kbuild b/nvidia-uvm/nvidia-uvm.Kbuild
index 0a4667b..370c6d8 100644
--- a/nvidia-uvm/nvidia-uvm.Kbuild
+++ b/nvidia-uvm/nvidia-uvm.Kbuild
@@ -136,3 +136,4 @@ NV_CONFTEST_TYPE_COMPILE_TESTS += mm_has_mmap_lock
 NV_CONFTEST_TYPE_COMPILE_TESTS += pnv_npu2_init_context
 NV_CONFTEST_TYPE_COMPILE_TESTS += kmem_cache_has_kobj_remove_work
 NV_CONFTEST_TYPE_COMPILE_TESTS += sysfs_slab_unlink
+NV_CONFTEST_TYPE_COMPILE_TESTS += vm_area_struct_has_const_vm_flags
diff --git a/nvidia-uvm/uvm8.c b/nvidia-uvm/uvm8.c
index 11cb373..4e84bbd 100644
--- a/nvidia-uvm/uvm8.c
+++ b/nvidia-uvm/uvm8.c
@@ -658,7 +658,7 @@ static int uvm_mmap(struct file *filp, struct vm_area_struct *vma)
     // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that
     // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK
     // with VM_IO, but that causes other mapping issues.
-    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;
+    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);
 
     vma->vm_ops = &uvm_vm_ops_managed;
 
-- 
2.20.1


````

## Original Target File(s)

### File: `nvidia-uvm/nvidia-uvm.Kbuild`

````Kbuild
###########################################################################
# Kbuild fragment for nvidia-uvm.ko
###########################################################################

UVM_BUILD_TYPE = release

MIN_VERSION    := 2
MIN_PATCHLEVEL := 6
MIN_SUBLEVEL   := 32

KERNEL_VERSION_NUMERIC := $(shell echo $$(( $(VERSION) * 65536 + $(PATCHLEVEL) * 256 + $(SUBLEVEL) )))
MIN_VERSION_NUMERIC    := $(shell echo $$(( $(MIN_VERSION) * 65536 + $(MIN_PATCHLEVEL) * 256 + $(MIN_SUBLEVEL) )))

KERNEL_NEW_ENOUGH_FOR_UVM := $(shell [ $(KERNEL_VERSION_NUMERIC) -ge $(MIN_VERSION_NUMERIC) ] && echo 1)

#
# Define NVIDIA_UVM_{SOURCES,OBJECTS}
#

NVIDIA_UVM_OBJECTS =
NVIDIA_UVM_UNSUPPORTED_SOURCE := nvidia-uvm/uvm_unsupported.c

ifeq ($(KERNEL_NEW_ENOUGH_FOR_UVM),1)
  include $(src)/nvidia-uvm/nvidia-uvm-sources.Kbuild
  NVIDIA_UVM_OBJECTS += $(patsubst %.c,%.o,\
      $(filter-out $(NVIDIA_UVM_UNSUPPORTED_SOURCE),$(NVIDIA_UVM_SOURCES)))
else
  NVIDIA_UVM_SOURCES = $(NVIDIA_UVM_UNSUPPORTED_SOURCE)
  NVIDIA_UVM_OBJECTS += $(patsubst %.c,%.o,$(NVIDIA_UVM_SOURCES))
endif

# Some linux kernel functions rely on being built with optimizations on and
# to work around this we put wrappers for them in a separate file that's built
# with optimizations on in debug builds and skipped in other builds.
# Notably gcc 4.4 supports per function optimization attributes that would be
# easier to use, but is too recent to rely on for now.
NVIDIA_UVM_DEBUG_OPTIMIZED_SOURCE := nvidia-uvm/uvm_debug_optimized.c
NVIDIA_UVM_DEBUG_OPTIMIZED_OBJECT := $(patsubst %.c,%.o,$(NVIDIA_UVM_DEBUG_OPTIMIZED_SOURCE))

ifneq ($(UVM_BUILD_TYPE),debug)
  # Only build the wrappers on debug builds
  NVIDIA_UVM_OBJECTS := $(filter-out $(NVIDIA_UVM_DEBUG_OPTIMIZED_OBJECT), $(NVIDIA_UVM_OBJECTS))
endif

obj-m += nvidia-uvm.o
nvidia-uvm-y := $(NVIDIA_UVM_OBJECTS)

NVIDIA_UVM_KO = nvidia-uvm/nvidia-uvm.ko

#
# Define nvidia-uvm.ko-specific CFLAGS.
#

ifeq ($(UVM_BUILD_TYPE),debug)
  NVIDIA_UVM_CFLAGS += -DDEBUG $(call cc-option,-Og,-O0) -g
else
  ifeq ($(UVM_BUILD_TYPE),develop)
    # -DDEBUG is required, in order to allow pr_devel() print statements to
    # work:
    NVIDIA_UVM_CFLAGS += -DDEBUG
    NVIDIA_UVM_CFLAGS += -DNVIDIA_UVM_DEVELOP
  endif
  NVIDIA_UVM_CFLAGS += -O2
endif

NVIDIA_UVM_CFLAGS += -DNVIDIA_UVM_ENABLED
NVIDIA_UVM_CFLAGS += -DNVIDIA_UNDEF_LEGACY_BIT_MACROS

NVIDIA_UVM_CFLAGS += -DLinux
NVIDIA_UVM_CFLAGS += -D__linux__
NVIDIA_UVM_CFLAGS += -I$(src)/nvidia-uvm

# Avoid even building HMM until the HMM patch is in the upstream kernel.
# Bug 1772628 has details.
NV_BUILD_SUPPORTS_HMM ?= 0

ifeq ($(NV_BUILD_SUPPORTS_HMM),1)
  NVIDIA_UVM_CFLAGS += -DNV_BUILD_SUPPORTS_HMM
endif

$(call ASSIGN_PER_OBJ_CFLAGS, $(NVIDIA_UVM_OBJECTS), $(NVIDIA_UVM_CFLAGS))

ifeq ($(UVM_BUILD_TYPE),debug)
  # Force optimizations on for the wrappers
  $(call ASSIGN_PER_OBJ_CFLAGS, $(NVIDIA_UVM_DEBUG_OPTIMIZED_OBJECT), $(NVIDIA_UVM_CFLAGS) -O2)
endif

#
# Register the conftests needed by nvidia-uvm.ko
#

NV_OBJECTS_DEPEND_ON_CONFTEST += $(NVIDIA_UVM_OBJECTS)

NV_CONFTEST_FUNCTION_COMPILE_TESTS += remap_page_range
NV_CONFTEST_FUNCTION_COMPILE_TESTS += remap_pfn_range
NV_CONFTEST_FUNCTION_COMPILE_TESTS += vm_insert_page
NV_CONFTEST_FUNCTION_COMPILE_TESTS += kmem_cache_create
NV_CONFTEST_FUNCTION_COMPILE_TESTS += address_space_init_once
NV_CONFTEST_FUNCTION_COMPILE_TESTS += kbasename
NV_CONFTEST_FUNCTION_COMPILE_TESTS += fatal_signal_pending
NV_CONFTEST_FUNCTION_COMPILE_TESTS += list_cut_position
NV_CONFTEST_FUNCTION_COMPILE_TESTS += vzalloc
NV_CONFTEST_FUNCTION_COMPILE_TESTS += wait_on_bit_lock_argument_count
NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data
NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data
NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA
NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_remove
NV_CONFTEST_FUNCTION_COMPILE_TESTS += bitmap_clear
NV_CONFTEST_FUNCTION_COMPILE_TESTS += usleep_range
NV_CONFTEST_FUNCTION_COMPILE_TESTS += radix_tree_empty
NV_CONFTEST_FUNCTION_COMPILE_TESTS += radix_tree_replace_slot
NV_CONFTEST_FUNCTION_COMPILE_TESTS += do_gettimeofday
NV_CONFTEST_FUNCTION_COMPILE_TESTS += ktime_get_raw_ts64

NV_CONFTEST_TYPE_COMPILE_TESTS += proc_dir_entry
NV_CONFTEST_TYPE_COMPILE_TESTS += irq_handler_t
NV_CONFTEST_TYPE_COMPILE_TESTS += outer_flush_all
NV_CONFTEST_TYPE_COMPILE_TESTS += vm_operations_struct
NV_CONFTEST_TYPE_COMPILE_TESTS += file_operations
NV_CONFTEST_TYPE_COMPILE_TESTS += task_struct
NV_CONFTEST_TYPE_COMPILE_TESTS += kuid_t
NV_CONFTEST_TYPE_COMPILE_TESTS += fault_flags
NV_CONFTEST_TYPE_COMPILE_TESTS += atomic64_type
NV_CONFTEST_TYPE_COMPILE_TESTS += address_space
NV_CONFTEST_TYPE_COMPILE_TESTS += backing_dev_info
NV_CONFTEST_TYPE_COMPILE_TESTS += mm_context_t
NV_CONFTEST_TYPE_COMPILE_TESTS += get_user_pages_remote
NV_CONFTEST_TYPE_COMPILE_TESTS += get_user_pages
NV_CONFTEST_TYPE_COMPILE_TESTS += vm_fault_has_address
NV_CONFTEST_TYPE_COMPILE_TESTS += vm_fault_present
NV_CONFTEST_TYPE_COMPILE_TESTS += vm_ops_fault_removed_vma_arg
NV_CONFTEST_TYPE_COMPILE_TESTS += vm_fault_t
NV_CONFTEST_TYPE_COMPILE_TESTS += proc_ops
NV_CONFTEST_TYPE_COMPILE_TESTS += timeval
NV_CONFTEST_TYPE_COMPILE_TESTS += mm_has_mmap_lock
NV_CONFTEST_TYPE_COMPILE_TESTS += pnv_npu2_init_context
NV_CONFTEST_TYPE_COMPILE_TESTS += kmem_cache_has_kobj_remove_work
NV_CONFTEST_TYPE_COMPILE_TESTS += sysfs_slab_unlink
NV_CONFTEST_TYPE_COMPILE_TESTS += vm_area_struct_has_const_vm_flags

````
### File: `nvidia-uvm/uvm8.c`

````c
/*******************************************************************************
    Copyright (c) 2015 NVIDIA Corporation

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to
    deal in the Software without restriction, including without limitation the
    rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
    sell copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

        The above copyright notice and this permission notice shall be
        included in all copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
    THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
    FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.

*******************************************************************************/

#include "uvm8_api.h"
#include "uvm8_global.h"
#include "uvm8_gpu_replayable_faults.h"
#include "uvm8_init.h"
#include "uvm8_tools_init.h"
#include "uvm8_lock.h"
#include "uvm8_test.h"
#include "uvm8_va_space.h"
#include "uvm8_va_range.h"
#include "uvm8_va_block.h"
#include "uvm8_tools.h"
#include "uvm_common.h"
#include "uvm_linux_ioctl.h"
#include "uvm8_hmm.h"
#include "uvm8_mem.h"

static struct cdev g_uvm_cdev;

// List of fault service contexts for CPU faults
static LIST_HEAD(g_cpu_fault_service_context_list);

static uvm_spinlock_t g_cpu_fault_service_context_list_lock;

static int alloc_cpu_fault_service_context_list(void)
{
    unsigned num_preallocated_contexts = 4;

    uvm_spin_lock_init(&g_cpu_fault_service_context_list_lock, UVM_LOCK_ORDER_LEAF);

    // Pre-allocate some fault service contexts for the CPU and add them to the global list
    while (num_preallocated_contexts-- > 0) {
        uvm_fault_service_block_context_t *service_context = uvm_kvmalloc(sizeof(*service_context));
        if (!service_context)
            return -ENOMEM;

        list_add(&service_context->cpu.service_context_list, &g_cpu_fault_service_context_list);
    }

    return 0;
}

static void free_cpu_fault_service_context_list(void)
{
    uvm_fault_service_block_context_t *service_context, *service_context_tmp;

    // Free fault service contexts for the CPU and add clear the global list
    list_for_each_entry_safe(service_context, service_context_tmp, &g_cpu_fault_service_context_list,
                             cpu.service_context_list) {
        uvm_kvfree(service_context);
    }
    INIT_LIST_HEAD(&g_cpu_fault_service_context_list);
}

// Get a fault service context from the global list or allocate a new one if there are no
// available entries
static uvm_fault_service_block_context_t *get_cpu_fault_service_context(void)
{
    uvm_fault_service_block_context_t *service_context;

    uvm_spin_lock(&g_cpu_fault_service_context_list_lock);

    service_context = list_first_entry_or_null(&g_cpu_fault_service_context_list, uvm_fault_service_block_context_t,
                                               cpu.service_context_list);

    if (service_context)
        list_del(&service_context->cpu.service_context_list);

    uvm_spin_unlock(&g_cpu_fault_service_context_list_lock);

    if (!service_context)
        service_context = uvm_kvmalloc(sizeof(*service_context));

    return service_context;
}

// Put a fault service context in the global list
static void put_cpu_fault_service_context(uvm_fault_service_block_context_t *service_context)
{
    uvm_spin_lock(&g_cpu_fault_service_context_list_lock);

    list_add(&service_context->cpu.service_context_list, &g_cpu_fault_service_context_list);

    uvm_spin_unlock(&g_cpu_fault_service_context_list_lock);
}

static int uvm_open(struct inode *inode, struct file *filp)
{
    NV_STATUS status = uvm_global_get_status();
    if (status == NV_OK)
        status = uvm_va_space_create(inode, filp);

    return -nv_status_to_errno(status);
}

static int uvm_release(struct inode *inode, struct file *filp)
{
    uvm_va_space_destroy(filp);

    return -nv_status_to_errno(uvm_global_get_status());
}

static void uvm_destroy_vma_managed(struct vm_area_struct *vma, bool is_uvm_teardown)
{
    uvm_va_range_t *va_range, *va_range_next;
    NvU64 size = 0;

    uvm_assert_rwsem_locked_write(&uvm_va_space_get(vma->vm_file)->lock);
    uvm_for_each_va_range_in_vma_safe(va_range, va_range_next, vma) {
        // On exit_mmap (process teardown), current->mm is cleared so
        // uvm_va_range_vma_current would return NULL.
        UVM_ASSERT(uvm_va_range_vma(va_range) == vma);
        UVM_ASSERT(va_range->node.start >= vma->vm_start);
        UVM_ASSERT(va_range->node.end   <  vma->vm_end);
        size += uvm_va_range_size(va_range);
        if (is_uvm_teardown)
            uvm_va_range_zombify(va_range);
        else
            uvm_va_range_destroy(va_range, NULL);
    }

    if (vma->vm_private_data) {
        uvm_vma_wrapper_destroy(vma->vm_private_data);
        vma->vm_private_data = NULL;
    }
    UVM_ASSERT(size == vma->vm_end - vma->vm_start);
}

static void uvm_destroy_vma_semaphore_pool(struct vm_area_struct *vma)
{
    uvm_va_space_t *va_space;
    uvm_va_range_t *va_range;

    va_space = uvm_va_space_get(vma->vm_file);
    uvm_assert_rwsem_locked(&va_space->lock);
    va_range = uvm_va_range_find(va_space, vma->vm_start);
    UVM_ASSERT(va_range &&
               va_range->node.start   == vma->vm_start &&
               va_range->node.end + 1 == vma->vm_end &&
               va_range->type == UVM_VA_RANGE_TYPE_SEMAPHORE_POOL);
    uvm_mem_unmap_cpu(va_range->semaphore_pool.mem);
}

// If a fault handler is not set, paths like handle_pte_fault in older kernels
// assume the memory is anonymous. That would make debugging this failure harder
// so we force it to fail instead.
static vm_fault_t uvm_vm_fault_sigbus(struct vm_area_struct *vma, struct vm_fault *vmf)
{
    UVM_DBG_PRINT_RL("Fault to address 0x%lx in disabled vma\n", nv_page_fault_va(vmf));
    return VM_FAULT_SIGBUS;
}

static vm_fault_t uvm_vm_fault_sigbus_wrapper(struct vm_fault *vmf)
{
#if defined(NV_VM_OPS_FAULT_REMOVED_VMA_ARG)
    return uvm_vm_fault_sigbus(vmf->vma, vmf);
#else
    return uvm_vm_fault_sigbus(NULL, vmf);
#endif
}

static struct vm_operations_struct uvm_vm_ops_disabled =
{
#if defined(NV_VM_OPS_FAULT_REMOVED_VMA_ARG)
    .fault = uvm_vm_fault_sigbus_wrapper
#else
    .fault = uvm_vm_fault_sigbus
#endif
};

static void uvm_disable_vma(struct vm_area_struct *vma)
{
    // In the case of fork, the kernel has already copied the old PTEs over to
    // the child process, so an access in the child might succeed instead of
    // causing a fault. To force a fault we'll unmap it directly here.
    //
    // Note that since the unmap works on file offset, not virtual address, this
    // unmaps both the old and new vmas.
    //
    // In the case of a move (mremap), the kernel will copy the PTEs over later,
    // so it doesn't matter if we unmap here. However, the new vma's open will
    // immediately be followed by a close on the old vma. We call
    // unmap_mapping_range for the close, which also unmaps the new vma because
    // they have the same file offset.
    unmap_mapping_range(vma->vm_file->f_mapping,
                        vma->vm_pgoff << PAGE_SHIFT,
                        vma->vm_end - vma->vm_start,
                        1);

    vma->vm_ops = &uvm_vm_ops_disabled;

    if (vma->vm_private_data) {
        uvm_vma_wrapper_destroy(vma->vm_private_data);
        vma->vm_private_data = NULL;
    }
}

// We can't return an error from uvm_vm_open so on failed splits
// we'll disable *both* vmas. This isn't great behavior for the
// user, but we don't have many options. We could leave the old VA
// range in place but that breaks the model of vmas always
// completely covering VA ranges. We'd have to be very careful
// handling later splits and closes of both that partially-covered
// VA range, and of the vmas which might or might not cover it any
// more.
//
// A failure likely means we're in OOM territory, so this should not
// be common by any means, and the process might die anyway.
static void uvm_vm_open_failure(struct vm_area_struct *original,
                                struct vm_area_struct *new)
{
    uvm_va_space_t *va_space = uvm_va_space_get(new->vm_file);
    static const bool is_uvm_teardown = false;

    UVM_ASSERT(va_space == uvm_va_space_get(original->vm_file));
    uvm_assert_rwsem_locked_write(&va_space->lock);

    uvm_destroy_vma_managed(original, is_uvm_teardown);
    uvm_disable_vma(original);
    uvm_disable_vma(new);
}

// vm_ops->open cases:
//
// 1) Parent vma is dup'd (fork)
//    This is undefined behavior in the UVM Programming Model. For convenience
//    the parent will continue operating properly, but the child is not
//    guaranteed access to the range.
//
// 2) Original vma is split (munmap, mprotect, mremap, mbind, etc)
//    The UVM Programming Model supports mbind always and supports mprotect if
//    HMM is present. Supporting either of those means all such splitting cases
//    must be handled. This involves splitting the va_range covering the split
//    location. Note that the kernel will never merge us back on two counts: we
//    set VM_MIXEDMAP and we have a ->close callback.
//
// 3) Original vma is moved (mremap)
//    This is undefined behavior in the UVM Programming Model. We'll get an open
//    on the new vma in which we disable operations on the new vma, then a close
//    on the old vma.
//
// Note that since we set VM_DONTEXPAND on the vma we're guaranteed that the vma
// will never increase in size, only shrink/split.
static void uvm_vm_open_managed(struct vm_area_struct *vma)
{
    uvm_va_space_t *va_space = uvm_va_space_get(vma->vm_file);
    uvm_va_range_t *va_range;
    struct vm_area_struct *original;
    NV_STATUS status;
    NvU64 new_end;

    // This is slightly ugly. We need to know the parent vma of this new one,
    // but we can't use the range tree to look up the original because that
    // doesn't handle a vma move operation.
    //
    // However, all of the old vma's fields have been copied into the new vma,
    // and open of the new vma is always called before close of the old (in
    // cases where close will be called immediately afterwards, like move).
    // vma->vm_private_data will thus still point to the original vma that we
    // set in mmap or open.
    //
    // Things to watch out for here:
    // - For splits, the old vma hasn't been adjusted yet so its vm_start and
    //   vm_end region will overlap with this vma's start and end.
    //
    // - For splits and moves, the new vma has not yet been inserted into the
    //   mm's list so vma->vm_prev and vma->vm_next cannot be used, nor will
    //   the new vma show up in find_vma and friends.
    original = ((uvm_vma_wrapper_t*)vma->vm_private_data)->vma;
    vma->vm_private_data = NULL;
    // On fork or move we want to simply disable the new vma
    if (vma->vm_mm != original->vm_mm ||
        (vma->vm_start != original->vm_start && vma->vm_end != original->vm_end)) {
        uvm_disable_vma(vma);
        return;
    }

    // At this point we are guaranteed that the mmap_lock is held in write
    // mode.
    uvm_record_lock_mmap_lock_write(current->mm);

    // Split vmas should always fall entirely within the old one, and be on one
    // side.
    UVM_ASSERT(vma->vm_start >= original->vm_start && vma->vm_end <= original->vm_end);
    UVM_ASSERT(vma->vm_start == original->vm_start || vma->vm_end == original->vm_end);

    // The vma is splitting, so create a new range under this vma if necessary.
    // The kernel handles splits in the middle of the vma by doing two separate
    // splits so we just have to handle one vma splitting in two here.
    if (vma->vm_start == original->vm_start)
        new_end = vma->vm_end - 1; // Left split (new_end is inclusive)
    else
        new_end = vma->vm_start - 1; // Right split (new_end is inclusive)

    uvm_va_space_down_write(va_space);

    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);
    if (!vma->vm_private_data) {
        uvm_vm_open_failure(original, vma);
        goto out;
    }

    // There can be multiple va_ranges under the vma already. Check if one spans
    // the new split boundary. If so, split it.
    va_range = uvm_va_range_find(va_space, new_end);
    UVM_ASSERT(va_range);
    UVM_ASSERT(uvm_va_range_vma_current(va_range) == original);
    if (va_range->node.end != new_end) {
        status = uvm_va_range_split(va_range, new_end, NULL);
        if (status != NV_OK) {
            UVM_DBG_PRINT("Failed to split VA range, destroying both: %s. "
                          "original vma [0x%lx, 0x%lx) new vma [0x%lx, 0x%lx)\n",
                          nvstatusToString(status),
                          original->vm_start, original->vm_end,
                          vma->vm_start, vma->vm_end);
            uvm_vm_open_failure(original, vma);
            goto out;
        }
    }

    // Point va_ranges to the new vma
    uvm_for_each_va_range_in_vma(va_range, vma) {
        UVM_ASSERT(uvm_va_range_vma_current(va_range) == original);
        va_range->managed.vma_wrapper = vma->vm_private_data;
    }

out:
    uvm_va_space_up_write(va_space);
    uvm_record_unlock_mmap_lock_write(current->mm);
}

static void uvm_vm_close_managed(struct vm_area_struct *vma)
{
    uvm_va_space_t *va_space = uvm_va_space_get(vma->vm_file);
    uvm_gpu_t *gpu;
    bool is_uvm_teardown = false;

    if (current->mm != NULL)
        uvm_record_lock_mmap_lock_write(current->mm);

    if (current->mm == NULL) {
        // current->mm will be NULL on process teardown. In that case, we want
        // to stop all user channels before unmapping the managed allocations to
        // avoid spurious MMU faults in the system log. That involves making RM
        // calls, so we have to do that with the VA space lock in read mode.
        uvm_va_space_down_read_rm(va_space);
        is_uvm_teardown = va_space->initialization_flags & UVM_INIT_FLAGS_DISABLE_TEARDOWN_ON_PROCESS_EXIT;
        if (!is_uvm_teardown && !atomic_read(&va_space->user_channels_stopped))
            uvm_va_space_stop_all_user_channels(va_space);
        uvm_va_space_up_read_rm(va_space);
    }

    // See uvm_mmap for why we need this in addition to mmap_lock
    uvm_va_space_down_write(va_space);

    uvm_destroy_vma_managed(vma, is_uvm_teardown);

    // Notify GPU address spaces that the fault buffer needs to be flushed to avoid finding stale entries
    // that can be attributed to new VA ranges reallocated at the same address
    for_each_gpu_in_mask(gpu, &va_space->registered_gpu_va_spaces) {
        uvm_gpu_va_space_t *gpu_va_space = uvm_gpu_va_space_get(va_space, gpu);
        UVM_ASSERT(gpu_va_space);

        gpu_va_space->needs_fault_buffer_flush = true;
    }
    uvm_va_space_up_write(va_space);

    if (current->mm != NULL)
        uvm_record_unlock_mmap_lock_write(current->mm);
}

static vm_fault_t uvm_vm_fault(struct vm_area_struct *vma, struct vm_fault *vmf)
{
    uvm_va_space_t *va_space = uvm_va_space_get(vma->vm_file);
    uvm_va_block_t *va_block;
    NvU64 fault_addr = nv_page_fault_va(vmf);
    bool is_write = vmf->flags & FAULT_FLAG_WRITE;
    NV_STATUS status = uvm_global_get_status();
    bool tools_enabled;
    bool major_fault = false;
    uvm_fault_service_block_context_t *service_context;

    if (status != NV_OK)
        goto convert_error;

    service_context = get_cpu_fault_service_context();
    if (!service_context) {
        status = NV_ERR_NO_MEMORY;
        goto convert_error;
    }

    service_context->cpu.wakeup_time_stamp = 0;

    // The mmap_lock might be held in write mode, but the mode doesn't matter
    // for the purpose of lock ordering and we don't rely on it being in write
    // anywhere so just record it as read mode in all cases.
    uvm_record_lock_mmap_lock_read(vma->vm_mm);

    do {
        bool do_sleep = false;
        if (status == NV_WARN_MORE_PROCESSING_REQUIRED) {
            NvU64 now = NV_GETTIME();
            if (now < service_context->cpu.wakeup_time_stamp)
                do_sleep = true;

            if (do_sleep)
                uvm_tools_record_throttling_start(va_space, fault_addr, UVM_CPU_ID);

            // Drop the VA space lock while we sleep
            uvm_va_space_up_read(va_space);

            // usleep_range is preferred because msleep has a 20ms granularity
            // and udelay uses a busy-wait loop. usleep_range uses high-resolution
            // timers and, by adding a range, the Linux scheduler may coalesce
            // our wakeup with others, thus saving some interrupts.
            if (do_sleep) {
                unsigned long nap_us = (service_context->cpu.wakeup_time_stamp - now) / 1000;

                usleep_range(nap_us, nap_us + nap_us / 2);
            }
        }

        uvm_va_space_down_read(va_space);

        if (do_sleep)
            uvm_tools_record_throttling_end(va_space, fault_addr, UVM_CPU_ID);

        status = uvm_va_block_find_create(va_space, fault_addr, &va_block);
        if (status != NV_OK) {
            UVM_ASSERT_MSG(status == NV_ERR_NO_MEMORY, "status: %s\n", nvstatusToString(status));
            goto out;
        }

        // Watch out, current->mm might not be vma->vm_mm
        UVM_ASSERT(vma == uvm_va_range_vma(va_block->va_range));

        // Loop until thrashing goes away.
        status = uvm_va_block_cpu_fault(va_block, fault_addr, is_write, service_context);
    } while (status == NV_WARN_MORE_PROCESSING_REQUIRED);

out:
    if (status != NV_OK) {
        UvmEventFatalReason reason;

        reason = uvm_tools_status_to_fatal_fault_reason(status);
        UVM_ASSERT(reason != UvmEventFatalReasonInvalid);

        uvm_tools_record_cpu_fatal_fault(va_space, fault_addr, is_write, reason);
    }

    tools_enabled = va_space->tools.enabled;

    if (status == NV_OK)
        uvm_gpu_retain_mask(&service_context->cpu.fault_gpus_to_check_for_ecc);

    uvm_va_space_up_read(va_space);
    uvm_record_unlock_mmap_lock_read(vma->vm_mm);

    if (status == NV_OK) {
        uvm_gpu_t *gpu;
        for_each_gpu_in_mask(gpu, &service_context->cpu.fault_gpus_to_check_for_ecc) {
            status = uvm_gpu_check_ecc_error(gpu);
            if (status != NV_OK)
                break;
        }
        uvm_gpu_release_mask(&service_context->cpu.fault_gpus_to_check_for_ecc);
    }

    if (tools_enabled)
        uvm_tools_flush_events();

    // Major faults involve I/O in order to resolve the fault.
    // If any pages were DMA'ed between the GPU and host memory, that makes it a major fault.
    // A process can also get statistics for major and minor faults by calling readproc().
    major_fault = service_context->cpu.fault_did_migrate;
    put_cpu_fault_service_context(service_context);

convert_error:
    switch (status) {
        case NV_OK:
            return VM_FAULT_NOPAGE | (major_fault ? VM_FAULT_MAJOR : 0);
        case NV_ERR_NO_MEMORY:
            return VM_FAULT_OOM;
        default:
            return VM_FAULT_SIGBUS;
    }
}

static vm_fault_t uvm_vm_fault_wrapper(struct vm_fault *vmf)
{
#if defined(NV_VM_OPS_FAULT_REMOVED_VMA_ARG)
    return uvm_vm_fault(vmf->vma, vmf);
#else
    return uvm_vm_fault(NULL, vmf);
#endif
}

static struct vm_operations_struct uvm_vm_ops_managed =
{
    .open         = uvm_vm_open_managed,
    .close        = uvm_vm_close_managed,

#if defined(NV_VM_OPS_FAULT_REMOVED_VMA_ARG)
    .fault        = uvm_vm_fault_wrapper,
    .page_mkwrite = uvm_vm_fault_wrapper,
#else
    .fault        = uvm_vm_fault,
    .page_mkwrite = uvm_vm_fault,
#endif
};

// vm operations on semaphore pool allocations only control CPU mappings. Unmapping GPUs,
// freeing the allocation, and destroying the va_range are handled by UVM_FREE.
static void uvm_vm_open_semaphore_pool(struct vm_area_struct *vma)
{
    struct vm_area_struct *origin_vma = (struct vm_area_struct *)vma->vm_private_data;
    uvm_va_space_t *va_space = uvm_va_space_get(origin_vma->vm_file);
    uvm_va_range_t *va_range;
    bool is_fork = (vma->vm_mm != origin_vma->vm_mm);
    NV_STATUS status;

    uvm_record_lock_mmap_lock_write(current->mm);

    uvm_va_space_down_write(va_space);

    va_range = uvm_va_range_find(va_space, origin_vma->vm_start);
    UVM_ASSERT(va_range);
    UVM_ASSERT_MSG(va_range->type == UVM_VA_RANGE_TYPE_SEMAPHORE_POOL &&
                   va_range->node.start == origin_vma->vm_start &&
                   va_range->node.end + 1 == origin_vma->vm_end,
                   "origin vma [0x%llx, 0x%llx); va_range [0x%llx, 0x%llx) type %d\n",
                   (NvU64)origin_vma->vm_start, (NvU64)origin_vma->vm_end, va_range->node.start,
                   va_range->node.end + 1, va_range->type);

    // Semaphore pool vmas do not have vma wrappers, but some functions will
    // assume vm_private_data is a wrapper.
    vma->vm_private_data = NULL;

    if (is_fork) {
        // If we forked, leave the parent vma alone.
        uvm_disable_vma(vma);
        // uvm_disable_vma unmaps in the parent as well; remap it.
        uvm_processor_mask_clear(&va_range->semaphore_pool.mem->mapped_on, UVM_CPU_ID);
        status = uvm_mem_map_cpu(va_range->semaphore_pool.mem, origin_vma);
        if (status != NV_OK) {
            UVM_DBG_PRINT("Failed to remap semaphore pool to CPU for parent after fork; status = %d (%s)",
                    status, nvstatusToString(status));
            origin_vma->vm_ops = &uvm_vm_ops_disabled;
        }
    }
    else {
        origin_vma->vm_private_data = NULL;
        origin_vma->vm_ops = &uvm_vm_ops_disabled;
        vma->vm_ops = &uvm_vm_ops_disabled;
        uvm_mem_unmap_cpu(va_range->semaphore_pool.mem);
    }

    uvm_va_space_up_write(va_space);

    uvm_record_unlock_mmap_lock_write(current->mm);
}

// vm operations on semaphore pool allocations only control CPU mappings. Unmapping GPUs,
// freeing the allocation, and destroying the va_range are handled by UVM_FREE.
static void uvm_vm_close_semaphore_pool(struct vm_area_struct *vma)
{
    uvm_va_space_t *va_space = uvm_va_space_get(vma->vm_file);

    if (current->mm != NULL)
        uvm_record_lock_mmap_lock_write(current->mm);

    uvm_va_space_down_read(va_space);

    uvm_destroy_vma_semaphore_pool(vma);

    uvm_va_space_up_read(va_space);

    if (current->mm != NULL)
        uvm_record_unlock_mmap_lock_write(current->mm);
}

static struct vm_operations_struct uvm_vm_ops_semaphore_pool =
{
    .open         = uvm_vm_open_semaphore_pool,
    .close        = uvm_vm_close_semaphore_pool,

#if defined(NV_VM_OPS_FAULT_REMOVED_VMA_ARG)
    .fault        = uvm_vm_fault_sigbus_wrapper,
#else
    .fault        = uvm_vm_fault_sigbus,
#endif
};

static int uvm_mmap(struct file *filp, struct vm_area_struct *vma)
{
    uvm_va_space_t *va_space = uvm_va_space_get(filp);
    uvm_va_range_t *va_range;
    NV_STATUS status = uvm_global_get_status();
    int ret = 0;
    bool vma_wrapper_allocated = false;

    if (status != NV_OK)
        return -nv_status_to_errno(status);


    uvm_record_lock_mmap_lock_write(current->mm);

    // UVM mappings are required to set offset == VA. This simplifies things
    // since we don't have to worry about address aliasing (except for fork,
    // handled separately) and it makes unmap_mapping_range simpler.
    if (vma->vm_start != (vma->vm_pgoff << PAGE_SHIFT)) {
        UVM_DBG_PRINT_RL("vm_start 0x%lx != vm_pgoff 0x%lx\n", vma->vm_start, vma->vm_pgoff << PAGE_SHIFT);
        ret = -EINVAL;
        goto out;
    }

    // Enforce shared read/writable mappings so we get all fault callbacks
    // without the kernel doing COW behind our backs. The user can still call
    // mprotect to change protections, but that will only hurt user space.
    if ((vma->vm_flags & (VM_SHARED|VM_READ|VM_WRITE)) !=
                         (VM_SHARED|VM_READ|VM_WRITE)) {
        UVM_DBG_PRINT_RL("User requested non-shared or non-writable mapping\n");
        ret = -EINVAL;
        goto out;
    }

    // VM_MIXEDMAP      Required to use vm_insert_page
    //
    // VM_DONTEXPAND    mremap can grow a vma in place without giving us any
    //                  callback. We need to prevent this so our ranges stay
    //                  up-to-date with the vma. This flag doesn't prevent
    //                  mremap from moving the mapping elsewhere, nor from
    //                  shrinking it. We can detect both of those cases however
    //                  with vm_ops->open() and vm_ops->close() callbacks.
    //
    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that
    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK
    // with VM_IO, but that causes other mapping issues.
    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;

    vma->vm_ops = &uvm_vm_ops_managed;

    // This identity assignment is needed so uvm_vm_open can find its parent vma
    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);
    if (!vma->vm_private_data) {
        ret = -ENOMEM;
        goto out;
    }
    vma_wrapper_allocated = true;

    // The kernel has taken mmap_lock in write mode, but that doesn't prevent
    // this va_space from being modified by the GPU fault path or from the ioctl
    // path where we don't have this mm for sure, so we have to lock the VA
    // space directly.
    uvm_va_space_down_write(va_space);

    // uvm_va_range_create_mmap will catch collisions. Below are some example
    // cases which can cause collisions. There may be others.
    // 1) An overlapping range was previously created with an ioctl, for example
    //    for an external mapping.
    // 2) This file was passed to another process via a UNIX domain socket
    status = uvm_va_range_create_mmap(va_space, vma->vm_private_data, NULL);

    if (status == NV_ERR_UVM_ADDRESS_IN_USE) {
        // If the mmap is for a semaphore pool, the VA range will have been
        // allocated by a previous ioctl, and the mmap just creates the CPU
        // mapping.
        va_range = uvm_va_range_find(va_space, vma->vm_start);
        if (va_range && va_range->node.start == vma->vm_start &&
                va_range->node.end + 1 == vma->vm_end &&
                va_range->type == UVM_VA_RANGE_TYPE_SEMAPHORE_POOL) {
            uvm_vma_wrapper_destroy(vma->vm_private_data);
            vma_wrapper_allocated = false;
            vma->vm_private_data = vma;
            vma->vm_ops = &uvm_vm_ops_semaphore_pool;
            status = uvm_mem_map_cpu(va_range->semaphore_pool.mem, vma);
        }
    }

    if (status != NV_OK) {
        UVM_DBG_PRINT_RL("Failed to create or map VA range for vma [0x%lx, 0x%lx): %s\n",
                         vma->vm_start, vma->vm_end, nvstatusToString(status));
        ret = -nv_status_to_errno(status);
    }

    uvm_va_space_up_write(va_space);

out:
    if (ret != 0 && vma_wrapper_allocated)
        uvm_vma_wrapper_destroy(vma->vm_private_data);

    uvm_record_unlock_mmap_lock_write(current->mm);

    return ret;
}

static long uvm_unlocked_ioctl(struct file *filp, unsigned int cmd, unsigned long arg)
{
    switch (cmd)
    {
        case UVM_DEINITIALIZE:
            return 0;

        UVM_ROUTE_CMD_STACK(UVM_INITIALIZE,                     uvm_api_initialize);
        UVM_ROUTE_CMD_STACK(UVM_IS_8_SUPPORTED,                 uvm_api_is_8_supported);
        UVM_ROUTE_CMD_STACK(UVM_PAGEABLE_MEM_ACCESS,            uvm_api_pageable_mem_access);
        UVM_ROUTE_CMD_STACK(UVM_PAGEABLE_MEM_ACCESS_ON_GPU,     uvm_api_pageable_mem_access_on_gpu);
        UVM_ROUTE_CMD_STACK(UVM_REGISTER_GPU,                   uvm_api_register_gpu);
        UVM_ROUTE_CMD_STACK(UVM_UNREGISTER_GPU,                 uvm_api_unregister_gpu);
        UVM_ROUTE_CMD_STACK(UVM_CREATE_RANGE_GROUP,             uvm_api_create_range_group);
        UVM_ROUTE_CMD_STACK(UVM_DESTROY_RANGE_GROUP,            uvm_api_destroy_range_group);
        UVM_ROUTE_CMD_STACK(UVM_ENABLE_PEER_ACCESS,             uvm_api_enable_peer_access);
        UVM_ROUTE_CMD_STACK(UVM_DISABLE_PEER_ACCESS,            uvm_api_disable_peer_access);
        UVM_ROUTE_CMD_STACK(UVM_SET_RANGE_GROUP,                uvm_api_set_range_group);
        UVM_ROUTE_CMD_ALLOC(UVM_MAP_EXTERNAL_ALLOCATION,        uvm_api_map_external_allocation);
        UVM_ROUTE_CMD_STACK(UVM_FREE,                           uvm_api_free);
        UVM_ROUTE_CMD_STACK(UVM_PREVENT_MIGRATION_RANGE_GROUPS, uvm_api_prevent_migration_range_groups);
        UVM_ROUTE_CMD_STACK(UVM_ALLOW_MIGRATION_RANGE_GROUPS,   uvm_api_allow_migration_range_groups);
        UVM_ROUTE_CMD_STACK(UVM_SET_PREFERRED_LOCATION,         uvm_api_set_preferred_location);
        UVM_ROUTE_CMD_STACK(UVM_UNSET_PREFERRED_LOCATION,       uvm_api_unset_preferred_location);
        UVM_ROUTE_CMD_STACK(UVM_SET_ACCESSED_BY,                uvm_api_set_accessed_by);
        UVM_ROUTE_CMD_STACK(UVM_UNSET_ACCESSED_BY,              uvm_api_unset_accessed_by);
        UVM_ROUTE_CMD_STACK(UVM_REGISTER_GPU_VASPACE,           uvm_api_register_gpu_va_space);
        UVM_ROUTE_CMD_STACK(UVM_UNREGISTER_GPU_VASPACE,         uvm_api_unregister_gpu_va_space);
        UVM_ROUTE_CMD_STACK(UVM_REGISTER_CHANNEL,               uvm_api_register_channel);
        UVM_ROUTE_CMD_STACK(UVM_UNREGISTER_CHANNEL,             uvm_api_unregister_channel);
        UVM_ROUTE_CMD_STACK(UVM_ENABLE_READ_DUPLICATION,        uvm_api_enable_read_duplication);
        UVM_ROUTE_CMD_STACK(UVM_DISABLE_READ_DUPLICATION,       uvm_api_disable_read_duplication);
        UVM_ROUTE_CMD_STACK(UVM_MIGRATE,                        uvm_api_migrate);
        UVM_ROUTE_CMD_STACK(UVM_ENABLE_SYSTEM_WIDE_ATOMICS,     uvm_api_enable_system_wide_atomics);
        UVM_ROUTE_CMD_STACK(UVM_DISABLE_SYSTEM_WIDE_ATOMICS,    uvm_api_disable_system_wide_atomics);
        UVM_ROUTE_CMD_STACK(UVM_TOOLS_READ_PROCESS_MEMORY,      uvm_api_tools_read_process_memory);
        UVM_ROUTE_CMD_STACK(UVM_TOOLS_WRITE_PROCESS_MEMORY,     uvm_api_tools_write_process_memory);
        UVM_ROUTE_CMD_STACK(UVM_TOOLS_GET_PROCESSOR_UUID_TABLE, uvm_api_tools_get_processor_uuid_table);
        UVM_ROUTE_CMD_STACK(UVM_MAP_DYNAMIC_PARALLELISM_REGION, uvm_api_map_dynamic_parallelism_region);
        UVM_ROUTE_CMD_STACK(UVM_UNMAP_EXTERNAL_ALLOCATION,      uvm_api_unmap_external_allocation);
        UVM_ROUTE_CMD_STACK(UVM_MIGRATE_RANGE_GROUP,            uvm_api_migrate_range_group);
        UVM_ROUTE_CMD_STACK(UVM_TOOLS_FLUSH_EVENTS,             uvm_api_tools_flush_events);
        UVM_ROUTE_CMD_ALLOC(UVM_ALLOC_SEMAPHORE_POOL,           uvm_api_alloc_semaphore_pool);
        UVM_ROUTE_CMD_STACK(UVM_CLEAN_UP_ZOMBIE_RESOURCES,      uvm_api_clean_up_zombie_resources);
    }

    // Try the test ioctls if none of the above matched
    return uvm8_test_ioctl(filp, cmd, arg);
}

static const struct file_operations uvm_fops =
{
    .open            = uvm_open,
    .release         = uvm_release,
    .mmap            = uvm_mmap,
    .unlocked_ioctl  = uvm_unlocked_ioctl,
#if NVCPU_IS_X86_64 && defined(NV_FILE_OPERATIONS_HAS_COMPAT_IOCTL)
    .compat_ioctl    = uvm_unlocked_ioctl,
#endif
    .owner           = THIS_MODULE,
};

int uvm8_init(dev_t uvm_base_dev)
{
    bool initialized_globals = false;
    bool added_device = false;
    bool initialized_tools = false;
    int ret = -ENODEV;
    dev_t uvm_dev = MKDEV(MAJOR(uvm_base_dev), NVIDIA_UVM_PRIMARY_MINOR_NUMBER);
    NV_STATUS status;

    status = uvm_global_init();
    if (status != NV_OK) {
        UVM_ERR_PRINT("uvm_global_init() failed: %s\n", nvstatusToString(status));
        goto error;
    }
    initialized_globals = true;

    uvm_init_character_device(&g_uvm_cdev, &uvm_fops);
    ret = cdev_add(&g_uvm_cdev, uvm_dev, 1);
    if (ret != 0) {
        UVM_ERR_PRINT("cdev_add (major %u, minor %u) failed: %d\n", MAJOR(uvm_dev), MINOR(uvm_dev), ret);
        goto error;
    }
    added_device = true;

    ret = uvm_tools_init(uvm_base_dev);
    if (ret != 0) {
        UVM_ERR_PRINT("uvm_tools_init() failed: %d\n", ret);
        goto error;
    }
    initialized_tools = true;

    ret = alloc_cpu_fault_service_context_list();
    if (ret != 0) {
        UVM_ERR_PRINT("alloc_cpu_fault_service_context_list failed: %d\n", ret);
        goto error;
    }

    uvm_hmm_init();

    return 0;

error:
    free_cpu_fault_service_context_list();

    if (initialized_tools)
        uvm_tools_exit();

    if (added_device)
        cdev_del(&g_uvm_cdev);

    if (initialized_globals)
        uvm_global_exit();

    return ret;
}

void uvm8_exit(void)
{
    free_cpu_fault_service_context_list();
    uvm_tools_exit();
    cdev_del(&g_uvm_cdev);

    uvm_global_exit();
}

NV_STATUS uvm8_initialize(UVM_INITIALIZE_PARAMS *params, struct file *filp)
{
    NV_STATUS status = NV_OK;
    uvm_va_space_t *va_space = uvm_va_space_get(filp);

    if ((params->flags & ~UVM_INIT_FLAGS_MASK))
        return NV_ERR_INVALID_ARGUMENT;

    uvm_down_write_mmap_lock(current->mm);
    uvm_va_space_down_write(va_space);

    if (va_space->initialized) {
        // Already initialized - check if parameters match
        if (params->flags != va_space->initialization_flags)
            status = NV_ERR_INVALID_ARGUMENT;
    }
    else {
        va_space->initialization_flags = params->flags;

        if (!(va_space->initialization_flags & UVM_INIT_FLAGS_DISABLE_HMM))
            status = uvm_hmm_mirror_register(va_space);

        if (status == NV_OK)
            va_space->initialized = true;
    }

    uvm_va_space_up_write(va_space);
    uvm_up_write_mmap_lock(current->mm);

    return status;
}

bool uvm_file_is_nvidia_uvm(struct file *filp)
{
    return (filp != NULL) && (filp->f_op == &uvm_fops);
}

````

## Full Trace Log

````log

Found 2 patch operation(s) to perform.
Fuzzy matching enabled with threshold: 0.70
debug: apply_patches_to_dir: applying 2 patch(es) to '.' (dry_run=true, fuzz=0.70)
debug:   [1/2] Applying patch for 'nvidia-uvm/nvidia-uvm.Kbuild' (1 hunk(s))
Applying patch to: nvidia-uvm/nvidia-uvm.Kbuild
debug:   apply_patch_to_file: target_dir='.', hunks=1, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'nvidia-uvm/nvidia-uvm.Kbuild'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-uvm")' on virtual path '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-uvm.Kbuild")' on virtual path '<TARGET_DIR>/nvidia-uvm'
trace:   Path safety verified: 'nvidia-uvm/nvidia-uvm.Kbuild' safely resolves to '<TARGET_DIR>/nvidia-uvm/nvidia-uvm.Kbuild'
debug:   Resolved safe target path: '<TARGET_DIR>/nvidia-uvm/nvidia-uvm.Kbuild'
debug:   Target file exists: '<TARGET_DIR>/nvidia-uvm/nvidia-uvm.Kbuild'. Reading content...
trace:     Read 5413 bytes (139 lines) from target file.
debug:   Applying patch logic to content in-memory...
debug: apply_patch_to_content: patch for 'nvidia-uvm/nvidia-uvm.Kbuild' (1 hunks), original content: 5413 bytes
debug:   apply_patch_to_lines called with 139 lines of original content.
debug: resolve_hunk_line_hints: evaluating 1 hunk(s) across 139 target lines
trace: Hunk::get_match_block: extracted 3 match line(s)
trace:   Hunk 1: already has explicit line hint 136
trace: resolve_hunk_line_hints: beginning relaxation pass 1
debug: resolve_hunk_line_hints: completed hint resolution. 1/1 hunk(s) have anchors.
debug: HunkApplier: initialized with 1 hunk(s) across 139 line(s) of target content (fuzz_factor=0.70, dry_run=true)
trace: HunkApplier::set_original_newline_status: original_ends_with_newline=true
debug: apply_hunk_to_lines: applying hunk with 4 line(s) against target with 139 line(s)
trace: Hunk::get_match_block: extracted 3 match line(s)
trace:   Match block: ["NV_CONFTEST_TYPE_COMPILE_TESTS += pnv_npu2_init_context", "NV_CONFTEST_TYPE_COMPILE_TESTS += kmem_cache_has_kobj_remove_work", "NV_CONFTEST_TYPE_COMPILE_TESTS += sysfs_slab_unlink"]
trace: Hunk::get_replace_block: extracted 4 replacement line(s)
trace:   Replace block: ["NV_CONFTEST_TYPE_COMPILE_TESTS += pnv_npu2_init_context", "NV_CONFTEST_TYPE_COMPILE_TESTS += kmem_cache_has_kobj_remove_work", "NV_CONFTEST_TYPE_COMPILE_TESTS += sysfs_slab_unlink", "NV_CONFTEST_TYPE_COMPILE_TESTS += vm_area_struct_has_const_vm_flags"]
trace: Hunk::has_changes: true
trace: Hunk::get_match_block: extracted 3 match line(s)
trace: Hunk::required_match_span: calculated required match span as 1 line(s) (first_match_idx=Some(2), last_match_idx=Some(2))
trace: DefaultHunkFinder::find_candidate_locations: match block len=3, required_match_span=1, target lines=139
trace:   find_hunk_location_internal: match_block has 3 lines (entropy=true), target has 139 lines
trace:   find_hunk_location_internal called for a hunk with 3 lines to match against 139 target lines.
trace:     Attempting exact match for hunk (match block has 3 line(s))...
trace: tie_break_with_line_number: strategy='exact', hint=Some(136), entropy=true
trace:       Found 1 exact match candidate at index: 135
trace:     tie_break: Only one match found for 'exact' match at index 135. No tie-break needed.
debug:     Strategy 1 (Exact): found unique exact match at index 135.
trace:   Pruned candidates by min_span 1: 1 -> 1 candidate(s)
trace: DefaultHunkFinder::find_candidate_locations: returning 1 candidate(s)
debug:   Found 1 candidate location(s) for hunk. Testing sequentially...
trace:   Evaluating candidate 1/1 at location HunkLocation { start_index: 135, length: 3 } (match_type: Exact)
debug:   Found location HunkLocation { start_index: 135, length: 3 } with match type Exact. Applying changes.
debug:   try_apply_hunk_at_location: target line 136 (length 3), match_type=Exact, total target lines=139.
trace: Hunk::get_match_block: extracted 3 match line(s)
trace:     Match block lines: 3 | Total hunk lines: 4
trace:     Target slice to replace: ["NV_CONFTEST_TYPE_COMPILE_TESTS += pnv_npu2_init_context", "NV_CONFTEST_TYPE_COMPILE_TESTS += kmem_cache_has_kobj_remove_work", "NV_CONFTEST_TYPE_COMPILE_TESTS += sysfs_slab_unlink"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
trace:     Applying hunk via exact logic.
trace: Hunk::get_replace_block: extracted 4 replacement line(s)
debug:     Exact match replacement generated 4 line(s) to replace 3 line(s).
trace:     Replacement block content: ["NV_CONFTEST_TYPE_COMPILE_TESTS += pnv_npu2_init_context", "NV_CONFTEST_TYPE_COMPILE_TESTS += kmem_cache_has_kobj_remove_work", "NV_CONFTEST_TYPE_COMPILE_TESTS += sysfs_slab_unlink", "NV_CONFTEST_TYPE_COMPILE_TESTS += vm_area_struct_has_const_vm_flags"]
trace:   Splicing final replacement block into target lines: range [135..138], replacement line count=4
  try_apply_hunk_at_location: successfully spliced hunk at line 136 (replaced 3 line(s), resulting target lines=140)
trace:     Replaced lines: ["NV_CONFTEST_TYPE_COMPILE_TESTS += pnv_npu2_init_context", "NV_CONFTEST_TYPE_COMPILE_TESTS += kmem_cache_has_kobj_remove_work", "NV_CONFTEST_TYPE_COMPILE_TESTS += sysfs_slab_unlink"]
debug:   Candidate 1/1 at HunkLocation { start_index: 135, length: 3 } succeeded! Hunk applied cleanly.
debug:   HunkApplier: hunk 1 application outcome: Applied { location: HunkLocation { start_index: 135, length: 3 }, match_type: Exact, replaced_lines: ["NV_CONFTEST_TYPE_COMPILE_TESTS += pnv_npu2_init_context", "NV_CONFTEST_TYPE_COMPILE_TESTS += kmem_cache_has_kobj_remove_work", "NV_CONFTEST_TYPE_COMPILE_TESTS += sysfs_slab_unlink"] }
trace:   HunkApplier: hunk 1 applied at line 136 (len=3), delta=1, target lines now=140
  Applying Hunk 1/1...
debug:     Successfully applied Hunk 1 at line 136 via Exact
trace:     Replaced lines:
trace:       - NV_CONFTEST_TYPE_COMPILE_TESTS += pnv_npu2_init_context
trace:       - NV_CONFTEST_TYPE_COMPILE_TESTS += kmem_cache_has_kobj_remove_work
trace:       - NV_CONFTEST_TYPE_COMPILE_TESTS += sysfs_slab_unlink
debug: HunkApplier::into_content: assembling final content from 140 line(s) (touched_eof=false, patch_ends_with_newline=true, original_ends_with_newline=true)
trace: HunkApplier::into_content: resulting content has 5481 bytes (140 lines, ends_with_newline=true)
  DRY RUN: Evaluated changes for 'nvidia-uvm/nvidia-uvm.Kbuild' (1 hunks, clean=true)
trace:   Generating diff for dry run...
debug:   [2/2] Applying patch for 'nvidia-uvm/uvm8.c' (1 hunk(s))
Applying patch to: nvidia-uvm/uvm8.c
debug:   apply_patch_to_file: target_dir='.', hunks=1, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'nvidia-uvm/uvm8.c'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia-uvm")' on virtual path '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("uvm8.c")' on virtual path '<TARGET_DIR>/nvidia-uvm'
trace:   Path safety verified: 'nvidia-uvm/uvm8.c' safely resolves to '<TARGET_DIR>/nvidia-uvm/uvm8.c'
debug:   Resolved safe target path: '<TARGET_DIR>/nvidia-uvm/uvm8.c'
debug:   Target file exists: '<TARGET_DIR>/nvidia-uvm/uvm8.c'. Reading content...
trace:     Read 34248 bytes (881 lines) from target file.
debug:   Applying patch logic to content in-memory...
debug: apply_patch_to_content: patch for 'nvidia-uvm/uvm8.c' (1 hunks), original content: 34248 bytes
debug:   apply_patch_to_lines called with 881 lines of original content.
debug: resolve_hunk_line_hints: evaluating 1 hunk(s) across 881 target lines
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:   Hunk 1: already has explicit line hint 658
trace: resolve_hunk_line_hints: beginning relaxation pass 1
debug: resolve_hunk_line_hints: completed hint resolution. 1/1 hunk(s) have anchors.
debug: HunkApplier: initialized with 1 hunk(s) across 881 line(s) of target content (fuzz_factor=0.70, dry_run=true)
trace: HunkApplier::set_original_newline_status: original_ends_with_newline=true
debug: apply_hunk_to_lines: applying hunk with 10 line(s) against target with 881 line(s)
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:   Match block: ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "- ", "2.20.1"]
trace: Hunk::get_replace_block: extracted 8 replacement line(s)
trace:   Replace block: ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "2.20.1"]
trace: Hunk::has_changes: true
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: Hunk::required_match_span: calculated required match span as 5 line(s) (first_match_idx=Some(3), last_match_idx=Some(7))
trace: DefaultHunkFinder::find_candidate_locations: match block len=9, required_match_span=5, target lines=881
trace:   find_hunk_location_internal: match_block has 9 lines (entropy=true), target has 881 lines
trace:   find_hunk_location_internal called for a hunk with 9 lines to match against 881 target lines.
trace:     Attempting exact match for hunk (match block has 9 line(s))...
trace: tie_break_with_line_number: strategy='exact', hint=Some(658), entropy=true
trace:       No exact matches found.
trace:     Strategy 1 (Exact): no exact match found.
trace:     Attempting exact match (ignoring trailing whitespace) for hunk (match block has 9 line(s))...
trace: tie_break_with_line_number: strategy='exact (ignoring whitespace)', hint=Some(658), entropy=true
trace:       No exact (ignoring whitespace) matches found.
trace:     Strategy 2 (Whitespace-insensitive): no match found.
debug:     Strategy 3 (Fuzzy): beginning flexible window fuzzy search (threshold=0.70, match block len=0.7)
trace:       Hunk match block (9 lines): ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "- ", "2.20.1"]
trace:       Searching with window sizes from 5 to 33 (hunk size: 9, fuzz distance: 24)
debug:       find_search_ranges: analyzing 9 match line(s) against 881 target line(s).
trace:         Identified 6 high-entropy candidate anchor line(s) (search_radius=18, max candidates to test=100)
debug:         Spatial consensus: 5 anchor(s) agree on start near line 663
debug:       Found anchor line (hunk line 2) with 1 occurrences.
trace:         Anchor text: '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Occurrence at target line 659: window estimated [640..708] (search radius +/-18)
trace:         Raw ranges before merging: [(639, 708)]
trace: merge_ranges: merging 1 input range(s): [(639, 708)]
trace: merge_ranges: result 1 disjoint range(s): [(639, 708)]
debug:       Search ranges merged: 1 disjoint range(s) covering 69/881 line(s) (92.2% pruned): [(639, 708)]
trace:     Using search ranges: [(639, 708)]
debug:       compute_scored_windows (parallel): evaluating 1479 candidate window(s) across 1 range(s) (window lengths 5..=33)
trace:         Match block length: 9, Target line count: 881, Search ranges: [(639, 708)]
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.323
trace:         score_window: window_len=9, match_len=9, line_score=0.222, ratio_lines=0.222, final_score=0.268
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.286
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.300
trace:         score_window: window_len=8, match_len=9, line_score=0.235, ratio_lines=0.235, final_score=0.284
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.290
trace:         score_window: window_len=11, match_len=9, line_score=0.110, ratio_lines=0.100, final_score=0.303
trace:         score_window: window_len=10, match_len=9, line_score=0.221, ratio_lines=0.211, final_score=0.237
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.293
trace:         score_window: window_len=7, match_len=9, line_score=0.250, ratio_lines=0.250, final_score=0.293
trace:         score_window: window_len=12, match_len=9, line_score=0.109, ratio_lines=0.095, final_score=0.268
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.252
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.295
trace:         score_window: window_len=22, match_len=9, line_score=0.412, ratio_lines=0.258, final_score=0.412
trace:         score_window: window_len=23, match_len=9, line_score=0.512, ratio_lines=0.312, final_score=0.512
trace:         score_window: window_len=5, match_len=9, line_score=0.143, ratio_lines=0.143, final_score=0.249
trace:         score_window: window_len=24, match_len=9, line_score=0.611, ratio_lines=0.364, final_score=0.611
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.213
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.237
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.237
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.258
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.239
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.257
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.245
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.265
trace:         score_window: window_len=11, match_len=9, line_score=0.110, ratio_lines=0.100, final_score=0.256
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.218
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.245
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.255
trace:         score_window: window_len=12, match_len=9, line_score=0.109, ratio_lines=0.095, final_score=0.247
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.249
trace:         score_window: window_len=21, match_len=9, line_score=0.415, ratio_lines=0.267, final_score=0.415
trace:         score_window: window_len=22, match_len=9, line_score=0.515, ratio_lines=0.323, final_score=0.515
trace:         score_window: window_len=23, match_len=9, line_score=0.615, ratio_lines=0.375, final_score=0.615
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.242
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.273
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.216
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.300
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.210
trace:         score_window: window_len=5, match_len=9, line_score=0.143, ratio_lines=0.143, final_score=0.312
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.185
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.228
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.257
trace:         score_window: window_len=11, match_len=9, line_score=0.110, ratio_lines=0.100, final_score=0.176
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.192
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.269
trace:         score_window: window_len=12, match_len=9, line_score=0.109, ratio_lines=0.095, final_score=0.161
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.195
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.254
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.293
trace:         score_window: window_len=13, match_len=9, line_score=0.109, ratio_lines=0.091, final_score=0.158
trace:         score_window: window_len=19, match_len=9, line_score=0.315, ratio_lines=0.214, final_score=0.355
trace:         score_window: window_len=20, match_len=9, line_score=0.417, ratio_lines=0.276, final_score=0.417
trace:         score_window: window_len=21, match_len=9, line_score=0.519, ratio_lines=0.333, final_score=0.519
trace:         score_window: window_len=5, match_len=9, line_score=0.143, ratio_lines=0.143, final_score=0.327
trace:         score_window: window_len=22, match_len=9, line_score=0.619, ratio_lines=0.387, final_score=0.619
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.276
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.272
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.248
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.283
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.259
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.250
trace:         score_window: window_len=10, match_len=9, line_score=0.221, ratio_lines=0.211, final_score=0.311
trace:         score_window: window_len=11, match_len=9, line_score=0.110, ratio_lines=0.100, final_score=0.235
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.301
trace:         score_window: window_len=12, match_len=9, line_score=0.109, ratio_lines=0.095, final_score=0.227
trace:         score_window: window_len=11, match_len=9, line_score=0.220, ratio_lines=0.200, final_score=0.293
trace:         score_window: window_len=13, match_len=9, line_score=0.109, ratio_lines=0.091, final_score=0.213
trace:         score_window: window_len=18, match_len=9, line_score=0.317, ratio_lines=0.222, final_score=0.366
trace:         score_window: window_len=19, match_len=9, line_score=0.420, ratio_lines=0.286, final_score=0.420
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.285
trace:         score_window: window_len=20, match_len=9, line_score=0.522, ratio_lines=0.345, final_score=0.522
trace:         score_window: window_len=21, match_len=9, line_score=0.622, ratio_lines=0.400, final_score=0.622
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=5, match_len=9, line_score=0.143, ratio_lines=0.143, final_score=0.220
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.275
trace:         score_window: window_len=9, match_len=9, line_score=0.222, ratio_lines=0.222, final_score=0.322
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.291
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.249
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.285
trace:         score_window: window_len=11, match_len=9, line_score=0.110, ratio_lines=0.100, final_score=0.239
trace:         score_window: window_len=10, match_len=9, line_score=0.221, ratio_lines=0.211, final_score=0.303
trace:         score_window: window_len=12, match_len=9, line_score=0.109, ratio_lines=0.095, final_score=0.224
trace:         score_window: window_len=17, match_len=9, line_score=0.319, ratio_lines=0.231, final_score=0.372
trace:         score_window: window_len=18, match_len=9, line_score=0.422, ratio_lines=0.296, final_score=0.426
trace:         score_window: window_len=19, match_len=9, line_score=0.525, ratio_lines=0.357, final_score=0.525
trace:         score_window: window_len=20, match_len=9, line_score=0.626, ratio_lines=0.414, final_score=0.626
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.293
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.313
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.183
trace:         score_window: window_len=5, match_len=9, line_score=0.143, ratio_lines=0.143, final_score=0.297
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.206
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.177
trace:         score_window: window_len=9, match_len=9, line_score=0.222, ratio_lines=0.222, final_score=0.308
trace:         score_window: window_len=11, match_len=9, line_score=0.110, ratio_lines=0.100, final_score=0.166
trace:         score_window: window_len=12, match_len=9, line_score=0.109, ratio_lines=0.095, final_score=0.165
trace:         score_window: window_len=8, match_len=9, line_score=0.235, ratio_lines=0.235, final_score=0.323
trace:         score_window: window_len=13, match_len=9, line_score=0.109, ratio_lines=0.091, final_score=0.164
trace:         score_window: window_len=16, match_len=9, line_score=0.320, ratio_lines=0.240, final_score=0.387
trace:         score_window: window_len=17, match_len=9, line_score=0.425, ratio_lines=0.308, final_score=0.442
trace:         score_window: window_len=18, match_len=9, line_score=0.528, ratio_lines=0.370, final_score=0.528
trace:         score_window: window_len=19, match_len=9, line_score=0.630, ratio_lines=0.429, final_score=0.630
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=10, match_len=9, line_score=0.221, ratio_lines=0.211, final_score=0.280
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.284
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.262
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.255
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.291
trace:         score_window: window_len=5, match_len=9, line_score=0.143, ratio_lines=0.143, final_score=0.312
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.269
trace:         score_window: window_len=11, match_len=9, line_score=0.110, ratio_lines=0.100, final_score=0.261
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.278
trace:         score_window: window_len=12, match_len=9, line_score=0.109, ratio_lines=0.095, final_score=0.258
trace:         score_window: window_len=15, match_len=9, line_score=0.322, ratio_lines=0.250, final_score=0.397
trace:         score_window: window_len=16, match_len=9, line_score=0.427, ratio_lines=0.320, final_score=0.453
trace:         score_window: window_len=17, match_len=9, line_score=0.531, ratio_lines=0.385, final_score=0.531
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.295
trace:         score_window: window_len=18, match_len=9, line_score=0.633, ratio_lines=0.444, final_score=0.633
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.252
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.258
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.280
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.274
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.215
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.267
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.239
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.268
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.266
trace:         score_window: window_len=11, match_len=9, line_score=0.110, ratio_lines=0.100, final_score=0.263
trace:         score_window: window_len=12, match_len=9, line_score=0.109, ratio_lines=0.095, final_score=0.190
trace:         score_window: window_len=14, match_len=9, line_score=0.324, ratio_lines=0.261, final_score=0.404
trace:         score_window: window_len=15, match_len=9, line_score=0.430, ratio_lines=0.333, final_score=0.462
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.285
trace:         score_window: window_len=16, match_len=9, line_score=0.534, ratio_lines=0.400, final_score=0.534
trace:         score_window: window_len=17, match_len=9, line_score=0.637, ratio_lines=0.462, final_score=0.637
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.238
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.209
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.270
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.279
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.209
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.266
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.227
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.272
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.229
trace:         score_window: window_len=11, match_len=9, line_score=0.110, ratio_lines=0.100, final_score=0.190
trace:         score_window: window_len=5, match_len=9, line_score=0.143, ratio_lines=0.143, final_score=0.249
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.266
trace:         score_window: window_len=13, match_len=9, line_score=0.326, ratio_lines=0.273, final_score=0.410
trace:         score_window: window_len=14, match_len=9, line_score=0.432, ratio_lines=0.348, final_score=0.468
trace:         score_window: window_len=15, match_len=9, line_score=0.537, ratio_lines=0.417, final_score=0.537
trace:         score_window: window_len=16, match_len=9, line_score=0.641, ratio_lines=0.480, final_score=0.641
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.192
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.200
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.235
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.180
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.238
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.191
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.205
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.249
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.233
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.241
trace:         score_window: window_len=5, match_len=9, line_score=0.143, ratio_lines=0.143, final_score=0.266
trace:         score_window: window_len=12, match_len=9, line_score=0.328, ratio_lines=0.286, final_score=0.414
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.233
trace:         score_window: window_len=13, match_len=9, line_score=0.435, ratio_lines=0.364, final_score=0.473
trace:         score_window: window_len=14, match_len=9, line_score=0.540, ratio_lines=0.435, final_score=0.540
trace:         score_window: window_len=15, match_len=9, line_score=0.644, ratio_lines=0.500, final_score=0.644
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.179
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.181
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.203
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.195
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.256
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.196
trace:         score_window: window_len=10, match_len=9, line_score=0.221, ratio_lines=0.211, final_score=0.332
trace:         score_window: window_len=5, match_len=9, line_score=0.143, ratio_lines=0.143, final_score=0.222
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.258
trace:         score_window: window_len=11, match_len=9, line_score=0.330, ratio_lines=0.300, final_score=0.432
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.262
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.271
trace:         score_window: window_len=12, match_len=9, line_score=0.437, ratio_lines=0.381, final_score=0.493
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.225
trace:         score_window: window_len=13, match_len=9, line_score=0.543, ratio_lines=0.455, final_score=0.543
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.278
trace:         score_window: window_len=14, match_len=9, line_score=0.648, ratio_lines=0.522, final_score=0.648
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.300
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=9, match_len=9, line_score=0.222, ratio_lines=0.222, final_score=0.338
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.157
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.205
trace:         score_window: window_len=5, match_len=9, line_score=0.143, ratio_lines=0.143, final_score=0.157
trace:         score_window: window_len=10, match_len=9, line_score=0.331, ratio_lines=0.316, final_score=0.440
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.258
trace:         score_window: window_len=11, match_len=9, line_score=0.440, ratio_lines=0.400, final_score=0.502
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.257
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.261
trace:         score_window: window_len=12, match_len=9, line_score=0.546, ratio_lines=0.476, final_score=0.546
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.269
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.274
trace:         score_window: window_len=13, match_len=9, line_score=0.652, ratio_lines=0.545, final_score=0.652
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.253
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=9, match_len=9, line_score=0.333, ratio_lines=0.333, final_score=0.505
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.286
trace:         score_window: window_len=8, match_len=9, line_score=0.235, ratio_lines=0.235, final_score=0.399
trace:         score_window: window_len=10, match_len=9, line_score=0.442, ratio_lines=0.421, final_score=0.546
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.310
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.225
trace:         score_window: window_len=11, match_len=9, line_score=0.549, ratio_lines=0.500, final_score=0.574
trace:         score_window: window_len=5, match_len=9, line_score=0.143, ratio_lines=0.143, final_score=0.309
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.241
trace:         score_window: window_len=12, match_len=9, line_score=0.656, ratio_lines=0.571, final_score=0.656
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.229
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.244
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.231
trace:         score_window: window_len=9, match_len=9, line_score=0.444, ratio_lines=0.444, final_score=0.632
trace:         score_window: window_len=8, match_len=9, line_score=0.353, ratio_lines=0.353, final_score=0.541
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.241
trace:         score_window: window_len=10, match_len=9, line_score=0.552, ratio_lines=0.526, final_score=0.640
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.257
trace:         score_window: window_len=7, match_len=9, line_score=0.250, ratio_lines=0.250, final_score=0.431
trace:         score_window: window_len=11, match_len=9, line_score=0.659, ratio_lines=0.600, final_score=0.704
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.278
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.245
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.176
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.229
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.236
trace:         score_window: window_len=9, match_len=9, line_score=0.556, ratio_lines=0.556, final_score=0.686
trace:         score_window: window_len=8, match_len=9, line_score=0.471, ratio_lines=0.471, final_score=0.678
trace:         score_window: window_len=10, match_len=9, line_score=0.663, ratio_lines=0.632, final_score=0.710
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.238
trace:         score_window: window_len=7, match_len=9, line_score=0.375, ratio_lines=0.375, final_score=0.584
trace:         score_window: window_len=6, match_len=9, line_score=0.267, ratio_lines=0.267, final_score=0.467
trace:         score_window: window_len=5, match_len=9, line_score=0.143, ratio_lines=0.143, final_score=0.269
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.249
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.267
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=9, match_len=9, line_score=0.667, ratio_lines=0.667, final_score=0.765
trace:         score_window: window_len=8, match_len=9, line_score=0.588, ratio_lines=0.588, final_score=0.721
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.188
trace:         score_window: window_len=7, match_len=9, line_score=0.500, ratio_lines=0.500, final_score=0.731
trace:         score_window: window_len=6, match_len=9, line_score=0.400, ratio_lines=0.400, final_score=0.633
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.187
trace:         score_window: window_len=5, match_len=9, line_score=0.286, ratio_lines=0.286, final_score=0.511
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.296
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=7, match_len=9, line_score=0.625, ratio_lines=0.625, final_score=0.799
trace:         score_window: window_len=6, match_len=9, line_score=0.533, ratio_lines=0.533, final_score=0.767
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.187
trace:         score_window: window_len=5, match_len=9, line_score=0.429, ratio_lines=0.429, final_score=0.696
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.197
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.199
trace:         score_window: window_len=6, match_len=9, line_score=0.667, ratio_lines=0.667, final_score=0.854
trace:         score_window: window_len=5, match_len=9, line_score=0.571, ratio_lines=0.571, final_score=0.821
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.245
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.158
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=9, match_len=9, line_score=0.667, ratio_lines=0.667, final_score=0.674
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.233
trace:         score_window: window_len=10, match_len=9, line_score=0.663, ratio_lines=0.632, final_score=0.663
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.155
trace:         score_window: window_len=11, match_len=9, line_score=0.659, ratio_lines=0.600, final_score=0.659
trace:         score_window: window_len=12, match_len=9, line_score=0.656, ratio_lines=0.571, final_score=0.656
trace:         score_window: window_len=13, match_len=9, line_score=0.652, ratio_lines=0.545, final_score=0.652
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.230
trace:         score_window: window_len=14, match_len=9, line_score=0.648, ratio_lines=0.522, final_score=0.648
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.153
trace:         score_window: window_len=15, match_len=9, line_score=0.644, ratio_lines=0.500, final_score=0.644
trace:         score_window: window_len=16, match_len=9, line_score=0.641, ratio_lines=0.480, final_score=0.641
trace:         score_window: window_len=17, match_len=9, line_score=0.637, ratio_lines=0.462, final_score=0.637
trace:         score_window: window_len=18, match_len=9, line_score=0.633, ratio_lines=0.444, final_score=0.633
trace:         score_window: window_len=19, match_len=9, line_score=0.630, ratio_lines=0.429, final_score=0.630
trace:         score_window: window_len=20, match_len=9, line_score=0.626, ratio_lines=0.414, final_score=0.626
trace:         score_window: window_len=21, match_len=9, line_score=0.622, ratio_lines=0.400, final_score=0.622
trace:         score_window: window_len=22, match_len=9, line_score=0.619, ratio_lines=0.387, final_score=0.619
trace:         score_window: window_len=12, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.228
trace:         score_window: window_len=23, match_len=9, line_score=0.615, ratio_lines=0.375, final_score=0.615
trace:         score_window: window_len=24, match_len=9, line_score=0.611, ratio_lines=0.364, final_score=0.611
trace:         score_window: window_len=25, match_len=9, line_score=0.607, ratio_lines=0.353, final_score=0.607
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.161
trace:         score_window: window_len=26, match_len=9, line_score=0.604, ratio_lines=0.343, final_score=0.604
trace:         score_window: window_len=27, match_len=9, line_score=0.600, ratio_lines=0.333, final_score=0.600
trace:         score_window: window_len=28, match_len=9, line_score=0.596, ratio_lines=0.324, final_score=0.596
trace:         score_window: window_len=29, match_len=9, line_score=0.593, ratio_lines=0.316, final_score=0.593
trace:         score_window: window_len=30, match_len=9, line_score=0.589, ratio_lines=0.308, final_score=0.589
trace:         score_window: window_len=31, match_len=9, line_score=0.585, ratio_lines=0.300, final_score=0.585
trace:         score_window: window_len=13, match_len=9, line_score=0.109, ratio_lines=0.091, final_score=0.262
trace:         score_window: window_len=32, match_len=9, line_score=0.581, ratio_lines=0.293, final_score=0.581
trace:         score_window: window_len=33, match_len=9, line_score=0.578, ratio_lines=0.286, final_score=0.578
trace:         score_window: window_len=9, match_len=9, line_score=0.556, ratio_lines=0.556, final_score=0.556
trace:         score_window: window_len=8, match_len=9, line_score=0.588, ratio_lines=0.588, final_score=0.588
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.233
trace:         score_window: window_len=10, match_len=9, line_score=0.552, ratio_lines=0.526, final_score=0.552
trace:         score_window: window_len=7, match_len=9, line_score=0.625, ratio_lines=0.625, final_score=0.625
trace:         score_window: window_len=11, match_len=9, line_score=0.549, ratio_lines=0.500, final_score=0.549
trace:         score_window: window_len=6, match_len=9, line_score=0.667, ratio_lines=0.667, final_score=0.667
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.236
trace:         score_window: window_len=12, match_len=9, line_score=0.546, ratio_lines=0.476, final_score=0.546
trace:         score_window: window_len=13, match_len=9, line_score=0.543, ratio_lines=0.455, final_score=0.543
trace:         score_window: window_len=14, match_len=9, line_score=0.540, ratio_lines=0.435, final_score=0.540
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.230
trace:         score_window: window_len=15, match_len=9, line_score=0.537, ratio_lines=0.417, final_score=0.537
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.184
trace:         score_window: window_len=16, match_len=9, line_score=0.534, ratio_lines=0.400, final_score=0.534
trace:         score_window: window_len=17, match_len=9, line_score=0.531, ratio_lines=0.385, final_score=0.531
trace:         score_window: window_len=18, match_len=9, line_score=0.528, ratio_lines=0.370, final_score=0.528
trace:         score_window: window_len=19, match_len=9, line_score=0.525, ratio_lines=0.357, final_score=0.525
trace:         score_window: window_len=20, match_len=9, line_score=0.522, ratio_lines=0.345, final_score=0.522
trace:         score_window: window_len=21, match_len=9, line_score=0.519, ratio_lines=0.333, final_score=0.519
trace:         score_window: window_len=22, match_len=9, line_score=0.515, ratio_lines=0.323, final_score=0.515
trace:         score_window: window_len=23, match_len=9, line_score=0.512, ratio_lines=0.312, final_score=0.512
trace:         score_window: window_len=24, match_len=9, line_score=0.509, ratio_lines=0.303, final_score=0.509
trace:         score_window: window_len=25, match_len=9, line_score=0.506, ratio_lines=0.294, final_score=0.506
trace:         score_window: window_len=26, match_len=9, line_score=0.503, ratio_lines=0.286, final_score=0.503
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.227
trace:         score_window: window_len=27, match_len=9, line_score=0.500, ratio_lines=0.278, final_score=0.500
trace:         score_window: window_len=28, match_len=9, line_score=0.497, ratio_lines=0.270, final_score=0.497
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.183
trace:         score_window: window_len=29, match_len=9, line_score=0.494, ratio_lines=0.263, final_score=0.494
trace:         score_window: window_len=30, match_len=9, line_score=0.491, ratio_lines=0.256, final_score=0.491
trace:         score_window: window_len=31, match_len=9, line_score=0.488, ratio_lines=0.250, final_score=0.488
trace:         score_window: window_len=32, match_len=9, line_score=0.485, ratio_lines=0.244, final_score=0.485
trace:         score_window: window_len=33, match_len=9, line_score=0.481, ratio_lines=0.238, final_score=0.481
trace:         score_window: window_len=9, match_len=9, line_score=0.444, ratio_lines=0.444, final_score=0.444
trace:         score_window: window_len=12, match_len=9, line_score=0.109, ratio_lines=0.095, final_score=0.255
trace:         score_window: window_len=8, match_len=9, line_score=0.471, ratio_lines=0.471, final_score=0.471
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.182
trace:         score_window: window_len=10, match_len=9, line_score=0.442, ratio_lines=0.421, final_score=0.442
trace:         score_window: window_len=7, match_len=9, line_score=0.500, ratio_lines=0.500, final_score=0.500
trace:         score_window: window_len=11, match_len=9, line_score=0.440, ratio_lines=0.400, final_score=0.440
trace:         score_window: window_len=6, match_len=9, line_score=0.533, ratio_lines=0.533, final_score=0.533
trace:         score_window: window_len=13, match_len=9, line_score=0.109, ratio_lines=0.091, final_score=0.241
trace:         score_window: window_len=12, match_len=9, line_score=0.437, ratio_lines=0.381, final_score=0.437
trace:         score_window: window_len=5, match_len=9, line_score=0.571, ratio_lines=0.571, final_score=0.571
trace:         score_window: window_len=13, match_len=9, line_score=0.435, ratio_lines=0.364, final_score=0.435
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.243
trace:         score_window: window_len=14, match_len=9, line_score=0.432, ratio_lines=0.348, final_score=0.432
trace:         score_window: window_len=15, match_len=9, line_score=0.430, ratio_lines=0.333, final_score=0.430
trace:         score_window: window_len=16, match_len=9, line_score=0.427, ratio_lines=0.320, final_score=0.427
trace:         score_window: window_len=17, match_len=9, line_score=0.425, ratio_lines=0.308, final_score=0.425
trace:         score_window: window_len=18, match_len=9, line_score=0.422, ratio_lines=0.296, final_score=0.422
trace:         score_window: window_len=19, match_len=9, line_score=0.420, ratio_lines=0.286, final_score=0.420
trace:         score_window: window_len=20, match_len=9, line_score=0.417, ratio_lines=0.276, final_score=0.417
trace:         score_window: window_len=21, match_len=9, line_score=0.415, ratio_lines=0.267, final_score=0.415
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.246
trace:         score_window: window_len=22, match_len=9, line_score=0.412, ratio_lines=0.258, final_score=0.412
trace:         score_window: window_len=23, match_len=9, line_score=0.410, ratio_lines=0.250, final_score=0.410
trace:         score_window: window_len=24, match_len=9, line_score=0.407, ratio_lines=0.242, final_score=0.407
trace:         score_window: window_len=25, match_len=9, line_score=0.405, ratio_lines=0.235, final_score=0.405
trace:         score_window: window_len=26, match_len=9, line_score=0.402, ratio_lines=0.229, final_score=0.402
trace:         score_window: window_len=27, match_len=9, line_score=0.400, ratio_lines=0.222, final_score=0.400
trace:         score_window: window_len=28, match_len=9, line_score=0.398, ratio_lines=0.216, final_score=0.398
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.239
trace:         score_window: window_len=29, match_len=9, line_score=0.395, ratio_lines=0.211, final_score=0.395
trace:         score_window: window_len=9, match_len=9, line_score=0.333, ratio_lines=0.333, final_score=0.333
trace:         score_window: window_len=8, match_len=9, line_score=0.353, ratio_lines=0.353, final_score=0.353
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.250
trace:         score_window: window_len=10, match_len=9, line_score=0.331, ratio_lines=0.316, final_score=0.331
trace:         score_window: window_len=7, match_len=9, line_score=0.375, ratio_lines=0.375, final_score=0.375
trace:         score_window: window_len=11, match_len=9, line_score=0.330, ratio_lines=0.300, final_score=0.330
trace:         score_window: window_len=6, match_len=9, line_score=0.400, ratio_lines=0.400, final_score=0.400
trace:         score_window: window_len=11, match_len=9, line_score=0.110, ratio_lines=0.100, final_score=0.268
trace:         score_window: window_len=12, match_len=9, line_score=0.328, ratio_lines=0.286, final_score=0.328
trace:         score_window: window_len=5, match_len=9, line_score=0.429, ratio_lines=0.429, final_score=0.429
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.219
trace:         score_window: window_len=13, match_len=9, line_score=0.326, ratio_lines=0.273, final_score=0.326
trace:         score_window: window_len=14, match_len=9, line_score=0.324, ratio_lines=0.261, final_score=0.324
trace:         score_window: window_len=12, match_len=9, line_score=0.109, ratio_lines=0.095, final_score=0.253
trace:         score_window: window_len=15, match_len=9, line_score=0.322, ratio_lines=0.250, final_score=0.322
trace:         score_window: window_len=16, match_len=9, line_score=0.320, ratio_lines=0.240, final_score=0.320
trace:         score_window: window_len=17, match_len=9, line_score=0.319, ratio_lines=0.231, final_score=0.319
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.219
trace:         score_window: window_len=18, match_len=9, line_score=0.317, ratio_lines=0.222, final_score=0.317
trace:         score_window: window_len=19, match_len=9, line_score=0.315, ratio_lines=0.214, final_score=0.315
trace:         score_window: window_len=9, match_len=9, line_score=0.222, ratio_lines=0.222, final_score=0.222
trace:         score_window: window_len=8, match_len=9, line_score=0.235, ratio_lines=0.235, final_score=0.235
trace:         score_window: window_len=10, match_len=9, line_score=0.221, ratio_lines=0.211, final_score=0.221
trace:         score_window: window_len=7, match_len=9, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.206
trace:         score_window: window_len=11, match_len=9, line_score=0.220, ratio_lines=0.200, final_score=0.220
trace:         score_window: window_len=6, match_len=9, line_score=0.267, ratio_lines=0.267, final_score=0.267
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.206
trace:         score_window: window_len=12, match_len=9, line_score=0.219, ratio_lines=0.190, final_score=0.219
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.233
trace:         score_window: window_len=5, match_len=9, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.209
trace:         score_window: window_len=13, match_len=9, line_score=0.217, ratio_lines=0.182, final_score=0.217
trace:         score_window: window_len=11, match_len=9, line_score=0.110, ratio_lines=0.100, final_score=0.219
trace:         score_window: window_len=14, match_len=9, line_score=0.216, ratio_lines=0.174, final_score=0.229
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.220
trace:         score_window: window_len=9, match_len=9, line_score=0.222, ratio_lines=0.222, final_score=0.222
trace:         score_window: window_len=12, match_len=9, line_score=0.109, ratio_lines=0.095, final_score=0.200
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.182
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.182
trace:         score_window: window_len=10, match_len=9, line_score=0.221, ratio_lines=0.211, final_score=0.229
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.249
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.191
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.238
trace:         score_window: window_len=11, match_len=9, line_score=0.220, ratio_lines=0.200, final_score=0.250
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.240
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.196
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.239
trace:         score_window: window_len=12, match_len=9, line_score=0.219, ratio_lines=0.190, final_score=0.219
trace:         score_window: window_len=11, match_len=9, line_score=0.110, ratio_lines=0.100, final_score=0.212
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.239
trace:         score_window: window_len=12, match_len=9, line_score=0.109, ratio_lines=0.095, final_score=0.195
trace:         score_window: window_len=13, match_len=9, line_score=0.217, ratio_lines=0.182, final_score=0.230
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.258
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.219
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.228
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.192
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.216
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.239
trace:         score_window: window_len=11, match_len=9, line_score=0.110, ratio_lines=0.100, final_score=0.175
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.217
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.228
trace:         score_window: window_len=12, match_len=9, line_score=0.109, ratio_lines=0.095, final_score=0.166
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.217
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.256
trace:         score_window: window_len=13, match_len=9, line_score=0.109, ratio_lines=0.091, final_score=0.165
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.187
trace:         score_window: window_len=14, match_len=9, line_score=0.216, ratio_lines=0.174, final_score=0.216
trace:         score_window: window_len=15, match_len=9, line_score=0.215, ratio_lines=0.167, final_score=0.215
trace:         score_window: window_len=11, match_len=9, line_score=0.110, ratio_lines=0.100, final_score=0.192
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.205
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.238
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.186
trace:         score_window: window_len=12, match_len=9, line_score=0.109, ratio_lines=0.095, final_score=0.209
trace:         score_window: window_len=11, match_len=9, line_score=0.110, ratio_lines=0.100, final_score=0.176
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.218
trace:         score_window: window_len=12, match_len=9, line_score=0.109, ratio_lines=0.095, final_score=0.175
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.191
trace:         score_window: window_len=13, match_len=9, line_score=0.217, ratio_lines=0.182, final_score=0.217
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.193
trace:         score_window: window_len=11, match_len=9, line_score=0.110, ratio_lines=0.100, final_score=0.213
trace:         score_window: window_len=14, match_len=9, line_score=0.216, ratio_lines=0.174, final_score=0.216
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.158
trace:         score_window: window_len=12, match_len=9, line_score=0.109, ratio_lines=0.095, final_score=0.217
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.175
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.149
trace:         score_window: window_len=13, match_len=9, line_score=0.217, ratio_lines=0.182, final_score=0.248
trace:         score_window: window_len=11, match_len=9, line_score=0.110, ratio_lines=0.100, final_score=0.148
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.200
trace:         score_window: window_len=12, match_len=9, line_score=0.219, ratio_lines=0.190, final_score=0.219
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.227
trace:         score_window: window_len=13, match_len=9, line_score=0.217, ratio_lines=0.182, final_score=0.217
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.118
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.220
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.126
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.117
trace:         score_window: window_len=11, match_len=9, line_score=0.110, ratio_lines=0.100, final_score=0.223
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.140
trace:         score_window: window_len=11, match_len=9, line_score=0.220, ratio_lines=0.200, final_score=0.220
trace:         score_window: window_len=12, match_len=9, line_score=0.219, ratio_lines=0.190, final_score=0.256
trace:         score_window: window_len=12, match_len=9, line_score=0.219, ratio_lines=0.190, final_score=0.219
trace:         score_window: window_len=13, match_len=9, line_score=0.217, ratio_lines=0.182, final_score=0.251
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.222
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.283
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.201
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.278
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.226
trace:         score_window: window_len=10, match_len=9, line_score=0.221, ratio_lines=0.211, final_score=0.311
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.230
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.204
trace:         score_window: window_len=11, match_len=9, line_score=0.220, ratio_lines=0.200, final_score=0.260
trace:         score_window: window_len=11, match_len=9, line_score=0.220, ratio_lines=0.200, final_score=0.306
trace:         score_window: window_len=12, match_len=9, line_score=0.219, ratio_lines=0.190, final_score=0.254
trace:         score_window: window_len=9, match_len=9, line_score=0.222, ratio_lines=0.222, final_score=0.298
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.269
trace:         score_window: window_len=13, match_len=9, line_score=0.217, ratio_lines=0.182, final_score=0.241
trace:         score_window: window_len=10, match_len=9, line_score=0.221, ratio_lines=0.211, final_score=0.293
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.233
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.230
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.264
trace:         score_window: window_len=9, match_len=9, line_score=0.222, ratio_lines=0.222, final_score=0.310
trace:         score_window: window_len=10, match_len=9, line_score=0.221, ratio_lines=0.211, final_score=0.269
trace:         score_window: window_len=8, match_len=9, line_score=0.235, ratio_lines=0.235, final_score=0.316
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.209
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.285
trace:         score_window: window_len=11, match_len=9, line_score=0.220, ratio_lines=0.200, final_score=0.263
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.280
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.240
trace:         score_window: window_len=8, match_len=9, line_score=0.235, ratio_lines=0.235, final_score=0.306
trace:         score_window: window_len=7, match_len=9, line_score=0.250, ratio_lines=0.250, final_score=0.312
trace:         score_window: window_len=12, match_len=9, line_score=0.219, ratio_lines=0.190, final_score=0.249
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.279
trace:         score_window: window_len=9, match_len=9, line_score=0.222, ratio_lines=0.222, final_score=0.282
trace:         score_window: window_len=5, match_len=9, line_score=0.143, ratio_lines=0.143, final_score=0.274
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.245
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.285
trace:         score_window: window_len=10, match_len=9, line_score=0.221, ratio_lines=0.211, final_score=0.274
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.289
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.242
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.251
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.251
trace:         score_window: window_len=11, match_len=9, line_score=0.220, ratio_lines=0.200, final_score=0.255
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.221
trace:         score_window: window_len=9, match_len=9, line_score=0.222, ratio_lines=0.222, final_score=0.280
trace:         score_window: window_len=8, match_len=9, line_score=0.235, ratio_lines=0.235, final_score=0.288
trace:         score_window: window_len=10, match_len=9, line_score=0.221, ratio_lines=0.211, final_score=0.260
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.249
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.246
trace:         score_window: window_len=5, match_len=9, line_score=0.143, ratio_lines=0.143, final_score=0.225
debug:       compute_scored_windows (parallel) complete: scored 1479 window(s). Best candidate score=0.875 at line 658 (len=7).
trace:       Top fuzzy match candidates:
trace:         - Index 657, Len 7: Score 0.875 (Ratio 0.875) | Content: ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:         - Index 656, Len 6: Score 0.854 (Ratio 0.854) | Content: ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", ""]
trace:         - Index 656, Len 8: Score 0.824 (Ratio 0.824) | Content: ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:         - Index 657, Len 8: Score 0.824 (Ratio 0.824) | Content: ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma"]
trace:         - Index 656, Len 5: Score 0.821 (Ratio 0.821) | Content: ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;"]
trace:         New best score: 0.323 (ratio 0.323 [l:0.111,w:0.413]) at index 639 (window len 9)
trace:         New best score: 0.674 (ratio 0.674 [l:0.091,w:0.000]) at index 639 (window len 13)
trace:         New best score: 0.697 (ratio 0.697 [l:0.207,w:0.000]) at index 639 (window len 20)
trace:         New best score: 0.709 (ratio 0.709 [l:0.412,w:0.709]) at index 639 (window len 25)
trace:         New best score: 0.713 (ratio 0.713 [l:0.424,w:0.713]) at index 640 (window len 24)
trace:         New best score: 0.717 (ratio 0.717 [l:0.438,w:0.717]) at index 641 (window len 23)
trace:         New best score: 0.722 (ratio 0.722 [l:0.452,w:0.722]) at index 642 (window len 22)
trace:         New best score: 0.726 (ratio 0.726 [l:0.467,w:0.726]) at index 643 (window len 21)
trace:         New best score: 0.730 (ratio 0.730 [l:0.483,w:0.730]) at index 644 (window len 20)
trace:         New best score: 0.735 (ratio 0.735 [l:0.500,w:0.735]) at index 645 (window len 19)
trace:         New best score: 0.739 (ratio 0.739 [l:0.519,w:0.739]) at index 646 (window len 18)
trace:         New best score: 0.743 (ratio 0.743 [l:0.538,w:0.743]) at index 647 (window len 17)
trace:         New best score: 0.748 (ratio 0.748 [l:0.560,w:0.748]) at index 648 (window len 16)
trace:         New best score: 0.752 (ratio 0.752 [l:0.583,w:0.752]) at index 649 (window len 15)
trace:         New best score: 0.756 (ratio 0.756 [l:0.609,w:0.756]) at index 650 (window len 14)
trace:         New best score: 0.760 (ratio 0.760 [l:0.636,w:0.760]) at index 651 (window len 13)
trace:         New best score: 0.765 (ratio 0.765 [l:0.667,w:0.765]) at index 652 (window len 12)
trace:         New best score: 0.769 (ratio 0.769 [l:0.700,w:0.769]) at index 653 (window len 11)
trace:         New best score: 0.773 (ratio 0.773 [l:0.737,w:0.773]) at index 654 (window len 10)
trace:         New best score: 0.778 (ratio 0.778 [l:0.778,w:0.778]) at index 655 (window len 9)
trace:         New best score: 0.799 (ratio 0.799 [l:0.625,w:0.873]) at index 655 (window len 7)
trace:         New best score: 0.824 (ratio 0.824 [l:0.824,w:0.824]) at index 656 (window len 8)
trace:         New best score: 0.854 (ratio 0.854 [l:0.667,w:0.935]) at index 656 (window len 6)
trace:         New best score: 0.875 (ratio 0.875 [l:0.875,w:0.875]) at index 657 (window len 7)
debug:     Strategy 3 (Fuzzy): 246 window(s) met threshold 0.70
trace:       Top 3 passing candidates: [("0.875", 658, 7), ("0.854", 657, 6), ("0.824", 657, 8)]
debug:     Top fuzzy candidate: start line 658 (len=7, score=0.875)
trace:       Adding candidate location at line 657 (len=6, score=0.854)
trace:       Adding candidate location at line 657 (len=8, score=0.824)
trace:       Adding candidate location at line 658 (len=8, score=0.824)
trace:       Adding candidate location at line 657 (len=5, score=0.821)
trace:       Adding candidate location at line 658 (len=6, score=0.800)
trace:       Adding candidate location at line 659 (len=6, score=0.800)
trace:       Adding candidate location at line 656 (len=7, score=0.799)
trace:       Adding candidate location at line 656 (len=9, score=0.778)
trace:       Adding candidate location at line 657 (len=9, score=0.778)
trace:       Adding candidate location at line 658 (len=9, score=0.778)
trace:       Adding candidate location at line 655 (len=10, score=0.773)
trace:       Adding candidate location at line 656 (len=10, score=0.773)
trace:       Adding candidate location at line 657 (len=10, score=0.773)
trace:       Adding candidate location at line 658 (len=10, score=0.773)
trace:       Adding candidate location at line 654 (len=11, score=0.769)
trace:       Adding candidate location at line 655 (len=11, score=0.769)
trace:       Adding candidate location at line 656 (len=11, score=0.769)
trace:       Adding candidate location at line 656 (len=6, score=0.767)
trace:       Adding candidate location at line 655 (len=9, score=0.765)
trace:       Reached maximum candidate limit (20), stopping candidate collection
debug:     Strategy 3 (Fuzzy): selected 20 candidate location(s)
trace:   Pruned candidates by min_span 5: 20 -> 20 candidate(s)
trace: DefaultHunkFinder::find_candidate_locations: returning 20 candidate(s)
debug:   Found 20 candidate location(s) for hunk. Testing sequentially...
trace:   Evaluating candidate 1/20 at location HunkLocation { start_index: 657, length: 7 } (match_type: Fuzzy { score: 0.875 })
debug:   Found location HunkLocation { start_index: 657, length: 7 } with match type Fuzzy { score: 0.875 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 658 (length 7), match_type=Fuzzy { score: 0.875 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=657, len=7
trace:       File content in matched range (7 line(s)): ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.875
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 1/20 at HunkLocation { start_index: 657, length: 7 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 2/20 at location HunkLocation { start_index: 656, length: 6 } (match_type: Fuzzy { score: 0.854437881708145 })
debug:   Found location HunkLocation { start_index: 656, length: 6 } with match type Fuzzy { score: 0.854437881708145 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 657 (length 6), match_type=Fuzzy { score: 0.854437881708145 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=656, len=6
trace:       File content in matched range (6 line(s)): ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", ""]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.667
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 5 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 4 line(s) missing from target file (hunk old_idx=5)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 2/20 at HunkLocation { start_index: 656, length: 6 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 3/20 at location HunkLocation { start_index: 656, length: 8 } (match_type: Fuzzy { score: 0.8235294222831726 })
debug:   Found location HunkLocation { start_index: 656, length: 8 } with match type Fuzzy { score: 0.8235294222831726 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 657 (length 8), match_type=Fuzzy { score: 0.8235294222831726 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=656, len=8
trace:       File content in matched range (8 line(s)): ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.824
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 3/20 at HunkLocation { start_index: 656, length: 8 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 4/20 at location HunkLocation { start_index: 657, length: 8 } (match_type: Fuzzy { score: 0.8235294222831726 })
debug:   Found location HunkLocation { start_index: 657, length: 8 } with match type Fuzzy { score: 0.8235294222831726 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 658 (length 8), match_type=Fuzzy { score: 0.8235294222831726 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=657, len=8
trace:       File content in matched range (8 line(s)): ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.824
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 7..8 (len=1)
trace:       Dynamic Indentation Update (Replace search): Hunk='', Target='    '
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('// This identity assignment is needed so uvm_vm_open can find its parent vma'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
debug:   Candidate 4/20 at HunkLocation { start_index: 657, length: 8 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 5/20 at location HunkLocation { start_index: 656, length: 5 } (match_type: Fuzzy { score: 0.8214285612106322 })
debug:   Found location HunkLocation { start_index: 656, length: 5 } with match type Fuzzy { score: 0.8214285612106322 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 657 (length 5), match_type=Fuzzy { score: 0.8214285612106322 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=656, len=5
trace:       File content in matched range (5 line(s)): ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.571
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 4 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:       DiffOp::Delete: 5 line(s) missing from target file (hunk old_idx=4)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 5/20 at HunkLocation { start_index: 656, length: 5 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 6/20 at location HunkLocation { start_index: 657, length: 6 } (match_type: Fuzzy { score: 0.800000011920929 })
debug:   Found location HunkLocation { start_index: 657, length: 6 } with match type Fuzzy { score: 0.800000011920929 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 658 (length 6), match_type=Fuzzy { score: 0.800000011920929 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=657, len=6
trace:       File content in matched range (6 line(s)): ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.800
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:       DiffOp::Delete: 3 line(s) missing from target file (hunk old_idx=6)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 6/20 at HunkLocation { start_index: 657, length: 6 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 7/20 at location HunkLocation { start_index: 658, length: 6 } (match_type: Fuzzy { score: 0.800000011920929 })
debug:   Found location HunkLocation { start_index: 658, length: 6 } with match type Fuzzy { score: 0.800000011920929 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 659 (length 6), match_type=Fuzzy { score: 0.800000011920929 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=658, len=6
trace:       File content in matched range (6 line(s)): ["    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.800
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Delete: 1 line(s) missing from target file (hunk old_idx=0)
trace:         Skipping stale context line missing in target: "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that"
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=1, file new_idx=0)
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 7/20 at HunkLocation { start_index: 658, length: 6 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 8/20 at location HunkLocation { start_index: 655, length: 7 } (match_type: Fuzzy { score: 0.7985497415065765 })
debug:   Found location HunkLocation { start_index: 655, length: 7 } with match type Fuzzy { score: 0.7985497415065765 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 656 (length 7), match_type=Fuzzy { score: 0.7985497415065765 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=655, len=7
trace:       File content in matched range (7 line(s)): ["    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", ""]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.625
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //                  with vm_ops->open() and vm_ops->close() callbacks.'
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 5 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 4 line(s) missing from target file (hunk old_idx=5)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 8/20 at HunkLocation { start_index: 655, length: 7 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 9/20 at location HunkLocation { start_index: 655, length: 9 } (match_type: Fuzzy { score: 0.7777777910232544 })
debug:   Found location HunkLocation { start_index: 655, length: 9 } with match type Fuzzy { score: 0.7777777910232544 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 656 (length 9), match_type=Fuzzy { score: 0.7777777910232544 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=655, len=9
trace:       File content in matched range (9 line(s)): ["    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.778
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //                  with vm_ops->open() and vm_ops->close() callbacks.'
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 9/20 at HunkLocation { start_index: 655, length: 9 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 10/20 at location HunkLocation { start_index: 656, length: 9 } (match_type: Fuzzy { score: 0.7777777910232544 })
debug:   Found location HunkLocation { start_index: 656, length: 9 } with match type Fuzzy { score: 0.7777777910232544 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 657 (length 9), match_type=Fuzzy { score: 0.7777777910232544 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=656, len=9
trace:       File content in matched range (9 line(s)): ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.778
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 8..9 (len=1)
trace:       Dynamic Indentation Update (Replace search): Hunk='', Target='    '
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('// This identity assignment is needed so uvm_vm_open can find its parent vma'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
debug:   Candidate 10/20 at HunkLocation { start_index: 656, length: 9 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 11/20 at location HunkLocation { start_index: 657, length: 9 } (match_type: Fuzzy { score: 0.7777777910232544 })
debug:   Found location HunkLocation { start_index: 657, length: 9 } with match type Fuzzy { score: 0.7777777910232544 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 658 (length 9), match_type=Fuzzy { score: 0.7777777910232544 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma", "    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=657, len=9
trace:       File content in matched range (9 line(s)): ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma", "    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.778
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 7..9 (len=2)
trace:       Dynamic Indentation Update (Replace search): Hunk='', Target='    '
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace:         1-to-1 replacement line validation [line 7]: is_removal=true, word_sim=0.000, char_sim=0.000
warning:     Fuzzy match rejected: Removal line "- " differs from target line "    // This identity assignment is needed so uvm_vm_open can find its parent vma" (sim_words=0.000, sim_chars=0.000, required=0.500).
debug:   Candidate 11/20 at HunkLocation { start_index: 657, length: 9 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 12/20 at location HunkLocation { start_index: 654, length: 10 } (match_type: Fuzzy { score: 0.7734567802445388 })
debug:   Found location HunkLocation { start_index: 654, length: 10 } with match type Fuzzy { score: 0.7734567802445388 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 655 (length 10), match_type=Fuzzy { score: 0.7734567802445388 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //                  shrinking it. We can detect both of those cases however", "    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=654, len=10
trace:       File content in matched range (10 line(s)): ["    //                  shrinking it. We can detect both of those cases however", "    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.737
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 3 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //                  shrinking it. We can detect both of those cases however'
trace:         Preserving inserted line: '    //                  with vm_ops->open() and vm_ops->close() callbacks.'
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=3)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 12/20 at HunkLocation { start_index: 654, length: 10 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 13/20 at location HunkLocation { start_index: 655, length: 10 } (match_type: Fuzzy { score: 0.7734567802445388 })
debug:   Found location HunkLocation { start_index: 655, length: 10 } with match type Fuzzy { score: 0.7734567802445388 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 656 (length 10), match_type=Fuzzy { score: 0.7734567802445388 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=655, len=10
trace:       File content in matched range (10 line(s)): ["    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.737
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //                  with vm_ops->open() and vm_ops->close() callbacks.'
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 9..10 (len=1)
trace:       Dynamic Indentation Update (Replace search): Hunk='', Target='    '
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('// This identity assignment is needed so uvm_vm_open can find its parent vma'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
debug:   Candidate 13/20 at HunkLocation { start_index: 655, length: 10 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 14/20 at location HunkLocation { start_index: 656, length: 10 } (match_type: Fuzzy { score: 0.7734567802445388 })
debug:   Found location HunkLocation { start_index: 656, length: 10 } with match type Fuzzy { score: 0.7734567802445388 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 657 (length 10), match_type=Fuzzy { score: 0.7734567802445388 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma", "    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=656, len=10
trace:       File content in matched range (10 line(s)): ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma", "    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.737
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 8..10 (len=2)
trace:       Dynamic Indentation Update (Replace search): Hunk='', Target='    '
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace:         1-to-1 replacement line validation [line 7]: is_removal=true, word_sim=0.000, char_sim=0.000
warning:     Fuzzy match rejected: Removal line "- " differs from target line "    // This identity assignment is needed so uvm_vm_open can find its parent vma" (sim_words=0.000, sim_chars=0.000, required=0.500).
debug:   Candidate 14/20 at HunkLocation { start_index: 656, length: 10 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 15/20 at location HunkLocation { start_index: 657, length: 10 } (match_type: Fuzzy { score: 0.7734567802445388 })
debug:   Found location HunkLocation { start_index: 657, length: 10 } with match type Fuzzy { score: 0.7734567802445388 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 658 (length 10), match_type=Fuzzy { score: 0.7734567802445388 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma", "    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);", "    if (!vma->vm_private_data) {"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=657, len=10
trace:       File content in matched range (10 line(s)): ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma", "    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);", "    if (!vma->vm_private_data) {"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.737
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 7..10 (len=3)
trace:       Dynamic Indentation Update (Replace search): Hunk='', Target='    '
trace:         Multi-line replacement (hunk_len=2, target_len=3). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 3 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('// This identity assignment is needed so uvm_vm_open can find its parent vma'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace: extract_primary_identifier: found call identifier 'uvm_vma_wrapper_alloc' in 'vma->vm_private_data = uvm_vma_wrapper_alloc(vma);'
trace:   find_statement_match_in_block: comparing target line 2 ('vma->vm_private_data = uvm_vma_wrapper_alloc(vma);'): word_ratio=0.000, char_ratio=0.036, combined=0.036
trace:   find_statement_match_in_block: comparing target line 3 ('if (!vma->vm_private_data) {'): word_ratio=0.000, char_ratio=0.061, combined=0.061
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
debug:   Candidate 15/20 at HunkLocation { start_index: 657, length: 10 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 16/20 at location HunkLocation { start_index: 653, length: 11 } (match_type: Fuzzy { score: 0.7691357893708312 })
debug:   Found location HunkLocation { start_index: 653, length: 11 } with match type Fuzzy { score: 0.7691357893708312 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 654 (length 11), match_type=Fuzzy { score: 0.7691357893708312 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //                  mremap from moving the mapping elsewhere, nor from", "    //                  shrinking it. We can detect both of those cases however", "    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=653, len=11
trace:       File content in matched range (11 line(s)): ["    //                  mremap from moving the mapping elsewhere, nor from", "    //                  shrinking it. We can detect both of those cases however", "    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.700
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 4 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //                  mremap from moving the mapping elsewhere, nor from'
trace:         Preserving inserted line: '    //                  shrinking it. We can detect both of those cases however'
trace:         Preserving inserted line: '    //                  with vm_ops->open() and vm_ops->close() callbacks.'
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=4)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 16/20 at HunkLocation { start_index: 653, length: 11 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 17/20 at location HunkLocation { start_index: 654, length: 11 } (match_type: Fuzzy { score: 0.7691357893708312 })
debug:   Found location HunkLocation { start_index: 654, length: 11 } with match type Fuzzy { score: 0.7691357893708312 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 655 (length 11), match_type=Fuzzy { score: 0.7691357893708312 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //                  shrinking it. We can detect both of those cases however", "    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=654, len=11
trace:       File content in matched range (11 line(s)): ["    //                  shrinking it. We can detect both of those cases however", "    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.700
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 3 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //                  shrinking it. We can detect both of those cases however'
trace:         Preserving inserted line: '    //                  with vm_ops->open() and vm_ops->close() callbacks.'
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=3)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 10..11 (len=1)
trace:       Dynamic Indentation Update (Replace search): Hunk='', Target='    '
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('// This identity assignment is needed so uvm_vm_open can find its parent vma'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
debug:   Candidate 17/20 at HunkLocation { start_index: 654, length: 11 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 18/20 at location HunkLocation { start_index: 655, length: 11 } (match_type: Fuzzy { score: 0.7691357893708312 })
debug:   Found location HunkLocation { start_index: 655, length: 11 } with match type Fuzzy { score: 0.7691357893708312 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 656 (length 11), match_type=Fuzzy { score: 0.7691357893708312 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma", "    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=655, len=11
trace:       File content in matched range (11 line(s)): ["    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma", "    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.700
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //                  with vm_ops->open() and vm_ops->close() callbacks.'
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 9..11 (len=2)
trace:       Dynamic Indentation Update (Replace search): Hunk='', Target='    '
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace:         1-to-1 replacement line validation [line 7]: is_removal=true, word_sim=0.000, char_sim=0.000
warning:     Fuzzy match rejected: Removal line "- " differs from target line "    // This identity assignment is needed so uvm_vm_open can find its parent vma" (sim_words=0.000, sim_chars=0.000, required=0.500).
debug:   Candidate 18/20 at HunkLocation { start_index: 655, length: 11 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 19/20 at location HunkLocation { start_index: 655, length: 6 } (match_type: Fuzzy { score: 0.766666680574417 })
debug:   Found location HunkLocation { start_index: 655, length: 6 } with match type Fuzzy { score: 0.766666680574417 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 656 (length 6), match_type=Fuzzy { score: 0.766666680574417 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=655, len=6
trace:       File content in matched range (6 line(s)): ["    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.533
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //                  with vm_ops->open() and vm_ops->close() callbacks.'
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 4 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:       DiffOp::Delete: 5 line(s) missing from target file (hunk old_idx=4)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 19/20 at HunkLocation { start_index: 655, length: 6 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 20/20 at location HunkLocation { start_index: 654, length: 9 } (match_type: Fuzzy { score: 0.7653846085071563 })
debug:   Found location HunkLocation { start_index: 654, length: 9 } with match type Fuzzy { score: 0.7653846085071563 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 655 (length 9), match_type=Fuzzy { score: 0.7653846085071563 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //                  shrinking it. We can detect both of those cases however", "    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=654, len=9
trace:       File content in matched range (9 line(s)): ["    //                  shrinking it. We can detect both of those cases however", "    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.667
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 3 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //                  shrinking it. We can detect both of those cases however'
trace:         Preserving inserted line: '    //                  with vm_ops->open() and vm_ops->close() callbacks.'
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=3)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:       DiffOp::Delete: 3 line(s) missing from target file (hunk old_idx=6)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 20/20 at HunkLocation { start_index: 654, length: 9 } failed with ContextNotFound. Backtracking...
debug:   Strict application failed for all 20 candidate(s). Retrying with fallback context reconciliation...
trace:   Evaluating candidate 1/20 with lenient reconciliation at location HunkLocation { start_index: 657, length: 7 }
debug:   Found location HunkLocation { start_index: 657, length: 7 } with match type Fuzzy { score: 0.875 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 658 (length 7), match_type=Fuzzy { score: 0.875 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=657, len=7
trace:       File content in matched range (7 line(s)): ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.875
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 2/20 with lenient reconciliation at location HunkLocation { start_index: 656, length: 6 }
debug:   Found location HunkLocation { start_index: 656, length: 6 } with match type Fuzzy { score: 0.854437881708145 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 657 (length 6), match_type=Fuzzy { score: 0.854437881708145 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=656, len=6
trace:       File content in matched range (6 line(s)): ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", ""]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '    //' -> '//'
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.667
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 5 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 4 line(s) missing from target file (hunk old_idx=5)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 3/20 with lenient reconciliation at location HunkLocation { start_index: 656, length: 8 }
debug:   Found location HunkLocation { start_index: 656, length: 8 } with match type Fuzzy { score: 0.8235294222831726 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 657 (length 8), match_type=Fuzzy { score: 0.8235294222831726 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=656, len=8
trace:       File content in matched range (8 line(s)): ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '    //' -> '//'
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.824
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 4/20 with lenient reconciliation at location HunkLocation { start_index: 657, length: 8 }
debug:   Found location HunkLocation { start_index: 657, length: 8 } with match type Fuzzy { score: 0.8235294222831726 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 658 (length 8), match_type=Fuzzy { score: 0.8235294222831726 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=657, len=8
trace:       File content in matched range (8 line(s)): ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    // This identity assignment is needed so uvm_vm_open can find its parent vma' -> '// This identity assignment is needed so uvm_vm_open can find its parent vma'
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.824
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 7..8 (len=1)
trace:       Dynamic Indentation Update (Replace search): Hunk='', Target='    '
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('// This identity assignment is needed so uvm_vm_open can find its parent vma'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
trace:   Evaluating candidate 5/20 with lenient reconciliation at location HunkLocation { start_index: 656, length: 5 }
debug:   Found location HunkLocation { start_index: 656, length: 5 } with match type Fuzzy { score: 0.8214285612106322 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 657 (length 5), match_type=Fuzzy { score: 0.8214285612106322 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=656, len=5
trace:       File content in matched range (5 line(s)): ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '    //' -> '//'
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.571
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 4 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:       DiffOp::Delete: 5 line(s) missing from target file (hunk old_idx=4)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 6/20 with lenient reconciliation at location HunkLocation { start_index: 657, length: 6 }
debug:   Found location HunkLocation { start_index: 657, length: 6 } with match type Fuzzy { score: 0.800000011920929 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 658 (length 6), match_type=Fuzzy { score: 0.800000011920929 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=657, len=6
trace:       File content in matched range (6 line(s)): ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.800
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:       DiffOp::Delete: 3 line(s) missing from target file (hunk old_idx=6)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 7/20 with lenient reconciliation at location HunkLocation { start_index: 658, length: 6 }
debug:   Found location HunkLocation { start_index: 658, length: 6 } with match type Fuzzy { score: 0.800000011920929 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 659 (length 6), match_type=Fuzzy { score: 0.800000011920929 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=658, len=6
trace:       File content in matched range (6 line(s)): ["    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.800
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Delete: 1 line(s) missing from target file (hunk old_idx=0)
trace:         Skipping stale context line missing in target: "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that"
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=1, file new_idx=0)
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 8/20 with lenient reconciliation at location HunkLocation { start_index: 655, length: 7 }
debug:   Found location HunkLocation { start_index: 655, length: 7 } with match type Fuzzy { score: 0.7985497415065765 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 656 (length 7), match_type=Fuzzy { score: 0.7985497415065765 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=655, len=7
trace:       File content in matched range (7 line(s)): ["    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", ""]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '    //                  with vm_ops->open() and vm_ops->close() callbacks.' -> '//                  with vm_ops->open() and vm_ops->close() callbacks.'
trace: normalize_line_delimiters: '    //' -> '//'
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.625
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //                  with vm_ops->open() and vm_ops->close() callbacks.'
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 5 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 4 line(s) missing from target file (hunk old_idx=5)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 9/20 with lenient reconciliation at location HunkLocation { start_index: 655, length: 9 }
debug:   Found location HunkLocation { start_index: 655, length: 9 } with match type Fuzzy { score: 0.7777777910232544 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 656 (length 9), match_type=Fuzzy { score: 0.7777777910232544 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=655, len=9
trace:       File content in matched range (9 line(s)): ["    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '    //                  with vm_ops->open() and vm_ops->close() callbacks.' -> '//                  with vm_ops->open() and vm_ops->close() callbacks.'
trace: normalize_line_delimiters: '    //' -> '//'
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.778
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //                  with vm_ops->open() and vm_ops->close() callbacks.'
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 10/20 with lenient reconciliation at location HunkLocation { start_index: 656, length: 9 }
debug:   Found location HunkLocation { start_index: 656, length: 9 } with match type Fuzzy { score: 0.7777777910232544 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 657 (length 9), match_type=Fuzzy { score: 0.7777777910232544 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=656, len=9
trace:       File content in matched range (9 line(s)): ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '    //' -> '//'
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    // This identity assignment is needed so uvm_vm_open can find its parent vma' -> '// This identity assignment is needed so uvm_vm_open can find its parent vma'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.778
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 8..9 (len=1)
trace:       Dynamic Indentation Update (Replace search): Hunk='', Target='    '
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('// This identity assignment is needed so uvm_vm_open can find its parent vma'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
trace:   Evaluating candidate 11/20 with lenient reconciliation at location HunkLocation { start_index: 657, length: 9 }
debug:   Found location HunkLocation { start_index: 657, length: 9 } with match type Fuzzy { score: 0.7777777910232544 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 658 (length 9), match_type=Fuzzy { score: 0.7777777910232544 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma", "    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=657, len=9
trace:       File content in matched range (9 line(s)): ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma", "    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    // This identity assignment is needed so uvm_vm_open can find its parent vma' -> '// This identity assignment is needed so uvm_vm_open can find its parent vma'
trace: normalize_line_delimiters: '    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);' -> 'vma->vm_private_data = uvm_vma_wrapper_alloc(vma)'
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.778
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 7..9 (len=2)
trace:       Dynamic Indentation Update (Replace search): Hunk='', Target='    '
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace:         1-to-1 replacement line validation [line 7]: is_removal=true, word_sim=0.000, char_sim=0.000
trace: normalize_line_delimiters: '-' -> '-'
trace: normalize_line_delimiters: '// This identity assignment is needed so uvm_vm_open can find its parent vma' -> '// This identity assignment is needed so uvm_vm_open can find its parent vma'
warning:     Fuzzy match rejected: Removal line "- " differs from target line "    // This identity assignment is needed so uvm_vm_open can find its parent vma" (sim_words=0.000, sim_chars=0.000, required=0.350).
trace:   Evaluating candidate 12/20 with lenient reconciliation at location HunkLocation { start_index: 654, length: 10 }
debug:   Found location HunkLocation { start_index: 654, length: 10 } with match type Fuzzy { score: 0.7734567802445388 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 655 (length 10), match_type=Fuzzy { score: 0.7734567802445388 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //                  shrinking it. We can detect both of those cases however", "    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=654, len=10
trace:       File content in matched range (10 line(s)): ["    //                  shrinking it. We can detect both of those cases however", "    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '    //                  shrinking it. We can detect both of those cases however' -> '//                  shrinking it. We can detect both of those cases however'
trace: normalize_line_delimiters: '    //                  with vm_ops->open() and vm_ops->close() callbacks.' -> '//                  with vm_ops->open() and vm_ops->close() callbacks.'
trace: normalize_line_delimiters: '    //' -> '//'
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.737
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 3 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //                  shrinking it. We can detect both of those cases however'
trace:         Preserving inserted line: '    //                  with vm_ops->open() and vm_ops->close() callbacks.'
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=3)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 13/20 with lenient reconciliation at location HunkLocation { start_index: 655, length: 10 }
debug:   Found location HunkLocation { start_index: 655, length: 10 } with match type Fuzzy { score: 0.7734567802445388 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 656 (length 10), match_type=Fuzzy { score: 0.7734567802445388 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=655, len=10
trace:       File content in matched range (10 line(s)): ["    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '    //                  with vm_ops->open() and vm_ops->close() callbacks.' -> '//                  with vm_ops->open() and vm_ops->close() callbacks.'
trace: normalize_line_delimiters: '    //' -> '//'
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    // This identity assignment is needed so uvm_vm_open can find its parent vma' -> '// This identity assignment is needed so uvm_vm_open can find its parent vma'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.737
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //                  with vm_ops->open() and vm_ops->close() callbacks.'
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 9..10 (len=1)
trace:       Dynamic Indentation Update (Replace search): Hunk='', Target='    '
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('// This identity assignment is needed so uvm_vm_open can find its parent vma'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
trace:   Evaluating candidate 14/20 with lenient reconciliation at location HunkLocation { start_index: 656, length: 10 }
debug:   Found location HunkLocation { start_index: 656, length: 10 } with match type Fuzzy { score: 0.7734567802445388 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 657 (length 10), match_type=Fuzzy { score: 0.7734567802445388 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma", "    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=656, len=10
trace:       File content in matched range (10 line(s)): ["    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma", "    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '    //' -> '//'
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    // This identity assignment is needed so uvm_vm_open can find its parent vma' -> '// This identity assignment is needed so uvm_vm_open can find its parent vma'
trace: normalize_line_delimiters: '    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);' -> 'vma->vm_private_data = uvm_vma_wrapper_alloc(vma)'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.737
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 8..10 (len=2)
trace:       Dynamic Indentation Update (Replace search): Hunk='', Target='    '
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace:         1-to-1 replacement line validation [line 7]: is_removal=true, word_sim=0.000, char_sim=0.000
trace: normalize_line_delimiters: '-' -> '-'
trace: normalize_line_delimiters: '// This identity assignment is needed so uvm_vm_open can find its parent vma' -> '// This identity assignment is needed so uvm_vm_open can find its parent vma'
warning:     Fuzzy match rejected: Removal line "- " differs from target line "    // This identity assignment is needed so uvm_vm_open can find its parent vma" (sim_words=0.000, sim_chars=0.000, required=0.350).
trace:   Evaluating candidate 15/20 with lenient reconciliation at location HunkLocation { start_index: 657, length: 10 }
debug:   Found location HunkLocation { start_index: 657, length: 10 } with match type Fuzzy { score: 0.7734567802445388 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 658 (length 10), match_type=Fuzzy { score: 0.7734567802445388 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma", "    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);", "    if (!vma->vm_private_data) {"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=657, len=10
trace:       File content in matched range (10 line(s)): ["    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma", "    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);", "    if (!vma->vm_private_data) {"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    // This identity assignment is needed so uvm_vm_open can find its parent vma' -> '// This identity assignment is needed so uvm_vm_open can find its parent vma'
trace: normalize_line_delimiters: '    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);' -> 'vma->vm_private_data = uvm_vma_wrapper_alloc(vma)'
trace: normalize_line_delimiters: '    if (!vma->vm_private_data) {' -> 'if (!vma->vm_private_data) {'
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.737
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 7..10 (len=3)
trace:       Dynamic Indentation Update (Replace search): Hunk='', Target='    '
trace:         Multi-line replacement (hunk_len=2, target_len=3). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 3 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('// This identity assignment is needed so uvm_vm_open can find its parent vma'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace: extract_primary_identifier: found call identifier 'uvm_vma_wrapper_alloc' in 'vma->vm_private_data = uvm_vma_wrapper_alloc(vma);'
trace:   find_statement_match_in_block: comparing target line 2 ('vma->vm_private_data = uvm_vma_wrapper_alloc(vma);'): word_ratio=0.000, char_ratio=0.036, combined=0.036
trace:   find_statement_match_in_block: comparing target line 3 ('if (!vma->vm_private_data) {'): word_ratio=0.000, char_ratio=0.061, combined=0.061
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
trace:   Evaluating candidate 16/20 with lenient reconciliation at location HunkLocation { start_index: 653, length: 11 }
debug:   Found location HunkLocation { start_index: 653, length: 11 } with match type Fuzzy { score: 0.7691357893708312 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 654 (length 11), match_type=Fuzzy { score: 0.7691357893708312 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //                  mremap from moving the mapping elsewhere, nor from", "    //                  shrinking it. We can detect both of those cases however", "    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=653, len=11
trace:       File content in matched range (11 line(s)): ["    //                  mremap from moving the mapping elsewhere, nor from", "    //                  shrinking it. We can detect both of those cases however", "    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", ""]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '    //                  mremap from moving the mapping elsewhere, nor from' -> '//                  mremap from moving the mapping elsewhere, nor from'
trace: normalize_line_delimiters: '    //                  shrinking it. We can detect both of those cases however' -> '//                  shrinking it. We can detect both of those cases however'
trace: normalize_line_delimiters: '    //                  with vm_ops->open() and vm_ops->close() callbacks.' -> '//                  with vm_ops->open() and vm_ops->close() callbacks.'
trace: normalize_line_delimiters: '    //' -> '//'
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.700
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 4 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //                  mremap from moving the mapping elsewhere, nor from'
trace:         Preserving inserted line: '    //                  shrinking it. We can detect both of those cases however'
trace:         Preserving inserted line: '    //                  with vm_ops->open() and vm_ops->close() callbacks.'
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=4)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 17/20 with lenient reconciliation at location HunkLocation { start_index: 654, length: 11 }
debug:   Found location HunkLocation { start_index: 654, length: 11 } with match type Fuzzy { score: 0.7691357893708312 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 655 (length 11), match_type=Fuzzy { score: 0.7691357893708312 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //                  shrinking it. We can detect both of those cases however", "    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=654, len=11
trace:       File content in matched range (11 line(s)): ["    //                  shrinking it. We can detect both of those cases however", "    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '    //                  shrinking it. We can detect both of those cases however' -> '//                  shrinking it. We can detect both of those cases however'
trace: normalize_line_delimiters: '    //                  with vm_ops->open() and vm_ops->close() callbacks.' -> '//                  with vm_ops->open() and vm_ops->close() callbacks.'
trace: normalize_line_delimiters: '    //' -> '//'
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    // This identity assignment is needed so uvm_vm_open can find its parent vma' -> '// This identity assignment is needed so uvm_vm_open can find its parent vma'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.700
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 3 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //                  shrinking it. We can detect both of those cases however'
trace:         Preserving inserted line: '    //                  with vm_ops->open() and vm_ops->close() callbacks.'
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=3)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 10..11 (len=1)
trace:       Dynamic Indentation Update (Replace search): Hunk='', Target='    '
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('// This identity assignment is needed so uvm_vm_open can find its parent vma'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
trace:   Evaluating candidate 18/20 with lenient reconciliation at location HunkLocation { start_index: 655, length: 11 }
debug:   Found location HunkLocation { start_index: 655, length: 11 } with match type Fuzzy { score: 0.7691357893708312 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 656 (length 11), match_type=Fuzzy { score: 0.7691357893708312 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma", "    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=655, len=11
trace:       File content in matched range (11 line(s)): ["    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;", "", "    // This identity assignment is needed so uvm_vm_open can find its parent vma", "    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '    //                  with vm_ops->open() and vm_ops->close() callbacks.' -> '//                  with vm_ops->open() and vm_ops->close() callbacks.'
trace: normalize_line_delimiters: '    //' -> '//'
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    // This identity assignment is needed so uvm_vm_open can find its parent vma' -> '// This identity assignment is needed so uvm_vm_open can find its parent vma'
trace: normalize_line_delimiters: '    vma->vm_private_data = uvm_vma_wrapper_alloc(vma);' -> 'vma->vm_private_data = uvm_vma_wrapper_alloc(vma)'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.700
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //                  with vm_ops->open() and vm_ops->close() callbacks.'
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:         Equal: preserving target line: ''
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 9..11 (len=2)
trace:       Dynamic Indentation Update (Replace search): Hunk='', Target='    '
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace:         1-to-1 replacement line validation [line 7]: is_removal=true, word_sim=0.000, char_sim=0.000
trace: normalize_line_delimiters: '-' -> '-'
trace: normalize_line_delimiters: '// This identity assignment is needed so uvm_vm_open can find its parent vma' -> '// This identity assignment is needed so uvm_vm_open can find its parent vma'
warning:     Fuzzy match rejected: Removal line "- " differs from target line "    // This identity assignment is needed so uvm_vm_open can find its parent vma" (sim_words=0.000, sim_chars=0.000, required=0.350).
trace:   Evaluating candidate 19/20 with lenient reconciliation at location HunkLocation { start_index: 655, length: 6 }
debug:   Found location HunkLocation { start_index: 655, length: 6 } with match type Fuzzy { score: 0.766666680574417 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 656 (length 6), match_type=Fuzzy { score: 0.766666680574417 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=655, len=6
trace:       File content in matched range (6 line(s)): ["    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '    //                  with vm_ops->open() and vm_ops->close() callbacks.' -> '//                  with vm_ops->open() and vm_ops->close() callbacks.'
trace: normalize_line_delimiters: '    //' -> '//'
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.533
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //                  with vm_ops->open() and vm_ops->close() callbacks.'
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 4 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:       DiffOp::Delete: 5 line(s) missing from target file (hunk old_idx=4)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 20/20 with lenient reconciliation at location HunkLocation { start_index: 654, length: 9 }
debug:   Found location HunkLocation { start_index: 654, length: 9 } with match type Fuzzy { score: 0.7653846085071563 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 655 (length 9), match_type=Fuzzy { score: 0.7653846085071563 }, total target lines=881.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["    //                  shrinking it. We can detect both of those cases however", "    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=654, len=9
trace:       File content in matched range (9 line(s)): ["    //                  shrinking it. We can detect both of those cases however", "    //                  with vm_ops->open() and vm_ops->close() callbacks.", "    //", "    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that", "    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK", "    // with VM_IO, but that causes other mapping issues.", "    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;", "", "    vma->vm_ops = &uvm_vm_ops_managed;"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: '    //                  shrinking it. We can detect both of those cases however' -> '//                  shrinking it. We can detect both of those cases however'
trace: normalize_line_delimiters: '    //                  with vm_ops->open() and vm_ops->close() callbacks.' -> '//                  with vm_ops->open() and vm_ops->close() callbacks.'
trace: normalize_line_delimiters: '    //' -> '//'
trace: normalize_line_delimiters: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that' -> '// Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace: normalize_line_delimiters: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK' -> '// so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace: normalize_line_delimiters: '    // with VM_IO, but that causes other mapping issues.' -> '// with VM_IO, but that causes other mapping issues.'
trace: normalize_line_delimiters: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;' -> 'vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND'
trace: normalize_line_delimiters: '' -> ''
trace: normalize_line_delimiters: '    vma->vm_ops = &uvm_vm_ops_managed;' -> 'vma->vm_ops = &uvm_vm_ops_managed'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.667
trace:       Initial Indentation Context: Hunk='    ', Target='    '
trace:       Active baseline indentation: hunk='    ', target='    '
trace:       DiffOp::Insert: preserving 3 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '    //                  shrinking it. We can detect both of those cases however'
trace:         Preserving inserted line: '    //                  with vm_ops->open() and vm_ops->close() callbacks.'
trace:         Preserving inserted line: '    //'
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=3)
trace:         Equal: preserving target line: '    // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that'
trace:         Equal: preserving target line: '    // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK'
trace:         Equal: preserving target line: '    // with VM_IO, but that causes other mapping issues.'
trace:         Equal: removing target line: '    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);'
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '    vma->vm_ops = &uvm_vm_ops_managed;'
trace:       DiffOp::Delete: 3 line(s) missing from target file (hunk old_idx=6)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
warning:   All 20 candidate location(s) exhausted. Hunk application failed with: Context not found
debug:   HunkApplier: hunk 1 application outcome: Failed(ContextNotFound)
  Applying Hunk 1/1...
warning:   Failed to apply Hunk 1. Context not found
debug: HunkApplier::into_content: assembling final content from 881 line(s) (touched_eof=false, patch_ends_with_newline=true, original_ends_with_newline=true)
trace: HunkApplier::into_content: resulting content has 34248 bytes (881 lines, ends_with_newline=true)
  DRY RUN: Evaluated changes for 'nvidia-uvm/uvm8.c' (1 hunks, clean=false)
trace:   Generating diff for dry run...
debug: apply_patches_to_dir: completed 2 patch(es). all_succeeded=true, all_applied_cleanly=false

>>> Operation 1/2

>>> Operation 2/2
error: --- FAILED to apply patch for: nvidia-uvm/uvm8.c
warning:   - Hunk 1 failed: Context not found
warning:     Failed Hunk Content:
warning:            // Using VM_DONTCOPY would be nice, but madvise(MADV_DOFORK) can reset that
warning:            // so we have to handle vm_open on fork anyway. We could disable MADV_DOFORK
warning:            // with VM_IO, but that causes other mapping issues.
warning:       -    vma->vm_flags |= VM_MIXEDMAP | VM_DONTEXPAND;
warning:       +    nv_vm_flags_set(vma, VM_MIXEDMAP | VM_DONTEXPAND);
warning:        
warning:            vma->vm_ops = &uvm_vm_ops_managed;
warning:        
warning:       -- 
warning:        2.20.1

--- Summary ---
Successful operations: 1
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
