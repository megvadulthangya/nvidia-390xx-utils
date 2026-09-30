# Mpatch Debug Report

> **Note:** This report has been partially anonymized. Please review for any remaining sensitive information before sharing.

- **Mpatch Version:** `1.6.4`
- **OS:** `linux`
- **Architecture:** `x86_64`
- **Timestamp (Unix):** `1790784821`

## Command Line

```sh
mpatch -vvvv --dry-run <INPUT_FILE> <TARGET_DIR>
```

## Input Patch File

````markdown
From ff44f24377756e4163ca1c544c5d6335257aee1e Mon Sep 17 00:00:00 2001
From: Andreas Beckmann <anbe@debian.org>
Date: Wed, 22 Sep 2021 08:49:14 +0200
Subject: [PATCH 1/2] backport error on unknown conftests

for easier backporting of future conftest.sh changes
---
 conftest.sh          | 12 ++++++++++++
 nvidia/nvidia.Kbuild |  4 ++--
 2 files changed, 14 insertions(+), 2 deletions(-)

diff --git a/conftest.sh b/conftest.sh
index e19b0ac..0c091ea 100755
--- a/conftest.sh
+++ b/conftest.sh
@@ -4646,6 +4646,18 @@ compile_test() {
 
             compile_check_conftest "$CODE" "NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE" "" "functions"
         ;;
+
+        # When adding a new conftest entry, please use the correct format for
+        # specifying the relevant upstream Linux kernel commit.
+        #
+        # <function> was added|removed|etc by commit <sha> ("<commit message")
+        # in <kernel-version> (<commit date>).
+
+        *)
+            # Unknown test name given
+            echo "Error: unknown conftest '$1' requested" >&2
+            exit 1
+        ;;
     esac
 }
 
diff --git a/nvidia/nvidia.Kbuild b/nvidia/nvidia.Kbuild
index d6995ca..39d8152 100644
--- a/nvidia/nvidia.Kbuild
+++ b/nvidia/nvidia.Kbuild
@@ -105,7 +105,7 @@ NV_OBJECTS_DEPEND_ON_CONFTEST += $(NVIDIA_OBJECTS)
 NV_CONFTEST_FUNCTION_COMPILE_TESTS += remap_pfn_range
 NV_CONFTEST_FUNCTION_COMPILE_TESTS += hash__remap_4k_pfn
 NV_CONFTEST_FUNCTION_COMPILE_TESTS += follow_pfn
-NV_CONFTEST_FUNCTION_COMPILE_TESTS += vmap
+#NV_CONFTEST_FUNCTION_COMPILE_TESTS += vmap
 NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_pages_uc
 NV_CONFTEST_FUNCTION_COMPILE_TESTS += list_is_first
 NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_memory_uc
@@ -127,7 +127,7 @@ NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace
 NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr
 NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error
 NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table
-NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table
+#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table
 NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot
 NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages
 NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled
-- 
2.20.1


````

## Original Target File(s)

### File: `conftest.sh`

````sh
#!/bin/sh

PATH="${PATH}:/bin:/sbin:/usr/bin"

# make sure we are in the directory containing this script
SCRIPTDIR=`dirname $0`
cd $SCRIPTDIR

#
# HOSTCC vs. CC - if a conftest needs to build and execute a test
# binary, like get_uname, then $HOSTCC needs to be used for this
# conftest in order for the host/build system to be able to execute
# it in X-compile environments.
# In all other cases, $CC should be used to minimize the risk of
# false failures due to conflicts with architecture specific header
# files.
#
CC="$1"
HOSTCC="$2"
ARCH=$3
ISYSTEM=`$CC -print-file-name=include 2> /dev/null`
SOURCES=$4
HEADERS=$SOURCES/include
OUTPUT=$5
XEN_PRESENT=1
PREEMPT_RT_PRESENT=0
KERNEL_ARCH="$ARCH"

if [ "$ARCH" = "i386" -o "$ARCH" = "x86_64" ]; then
    if [ -d "$SOURCES/arch/x86" ]; then
        KERNEL_ARCH="x86"
    fi
fi

HEADERS_ARCH="$SOURCES/arch/$KERNEL_ARCH/include"

# VGX_BUILD parameter defined only for VGX builds (vGPU Host driver)
# VGX_KVM_BUILD parameter defined only vGPU builds on KVM hypervisor
# GRID_BUILD parameter defined only for GRID builds (GRID Guest driver)

test_xen() {
    #
    # Determine if the target kernel is a Xen kernel. It used to be
    # sufficient to check for CONFIG_XEN, but the introduction of
    # modular para-virtualization (CONFIG_PARAVIRT, etc.) and
    # Xen guest support, it is no longer possible to determine the
    # target environment at build time. Therefore, if both
    # CONFIG_XEN and CONFIG_PARAVIRT are present, text_xen() treats
    # the kernel as a stand-alone kernel.
    #
    if ! test_configuration_option CONFIG_XEN ||
         test_configuration_option CONFIG_PARAVIRT; then
        XEN_PRESENT=0
    fi
}

append_conftest() {
    #
    # Echo data from stdin: this is a transitional function to make it easier
    # to port conftests from drivers with parallel conftest generation to
    # older driver versions
    #

    while read LINE; do
        echo ${LINE}
    done
}

translate_and_find_header_files() {
    # Inputs:
    #   $1: a parent directory (full path), in which to search
    #   $2: a list of relative file paths
    #
    # This routine creates an upper case, underscore version of each of the
    # relative file paths, and uses that as the token to either define or
    # undefine in a C header file. For example, linux/fence.h becomes
    # NV_LINUX_FENCE_H_PRESENT, and that is either defined or undefined, in the
    # output (which goes to stdout, just like the rest of this file).

    local parent_dir=$1
    shift

    for file in $@; do
        local file_define=NV_`echo $file | tr '/.' '_' | tr '-' '_' | tr 'a-z' 'A-Z'`_PRESENT
        if [ -f $parent_dir/$file -o -f $OUTPUT/include/$file ]; then
            echo "#define $file_define"
        else
            echo "#undef $file_define"
        fi
    done
}

test_headers() {
    #
    # Determine which header files (of a set that may or may not be
    # present) are provided by the target kernel.
    #
    FILES="acpi/video.h"
    FILES="$FILES asm/system.h"
    FILES="$FILES drm/drmP.h"
    FILES="$FILES drm/drm_auth.h"
    FILES="$FILES drm/drm_gem.h"
    FILES="$FILES drm/drm_crtc.h"
    FILES="$FILES drm/drm_atomic.h"
    FILES="$FILES drm/drm_atomic_helper.h"
    FILES="$FILES drm/drm_encoder.h"
    FILES="$FILES drm/drm_atomic_uapi.h"
    FILES="$FILES drm/drm_drv.h"
    FILES="$FILES drm/drm_framebuffer.h"
    FILES="$FILES drm/drm_connector.h"
    FILES="$FILES drm/drm_probe_helper.h"
    FILES="$FILES drm/drm_prime.h"
    FILES="$FILES drm/drm_plane.h"
    FILES="$FILES drm/drm_vblank.h"
    FILES="$FILES drm/drm_file.h"
    FILES="$FILES drm/drm_ioctl.h"
    FILES="$FILES drm/drm_device.h"
    FILES="$FILES generated/autoconf.h"
    FILES="$FILES generated/compile.h"
    FILES="$FILES generated/utsrelease.h"
    FILES="$FILES linux/efi.h"
    FILES="$FILES linux/kconfig.h"
    FILES="$FILES linux/screen_info.h"
    FILES="$FILES linux/semaphore.h"
    FILES="$FILES linux/printk.h"
    FILES="$FILES linux/ratelimit.h"
    FILES="$FILES linux/prio_tree.h"
    FILES="$FILES linux/log2.h"
    FILES="$FILES linux/of.h"
    FILES="$FILES linux/bug.h"
    FILES="$FILES linux/sched/signal.h"
    FILES="$FILES linux/sched/task.h"
    FILES="$FILES linux/sched/task_stack.h"
    FILES="$FILES xen/ioemu.h"
    FILES="$FILES linux/fence.h"
    FILES="$FILES linux/ktime.h"
    FILES="$FILES linux/dma-resv.h"
    FILES="$FILES linux/dma-map-ops.h"
    FILES="$FILES linux/stdarg.h"
    FILES="$FILES linux/iosys-map.h"

    # Arch specific headers which need testing
    FILES_ARCH="asm/book3s/64/hash-64k.h"
    FILES_ARCH="$FILES_ARCH asm/set_memory.h"
    FILES_ARCH="$FILES_ARCH asm/powernv.h"
    FILES_ARCH="$FILES_ARCH asm/tlbflush.h"
    FILES_ARCH="$FILES_ARCH asm/pgtable_types.h"

    translate_and_find_header_files $HEADERS      $FILES
    translate_and_find_header_files $HEADERS_ARCH $FILES_ARCH
}

build_cflags() {
    BASE_CFLAGS="-O2 -D__KERNEL__ \
-DKBUILD_BASENAME=\"#conftest$$\" -DKBUILD_MODNAME=\"#conftest$$\" \
-nostdinc -isystem $ISYSTEM"

    if [ "$OUTPUT" != "$SOURCES" ]; then
        OUTPUT_CFLAGS="-I$OUTPUT/include2 -I$OUTPUT/include"
        if [ -f "$OUTPUT/include/generated/autoconf.h" ]; then
            AUTOCONF_FILE="$OUTPUT/include/generated/autoconf.h"
        else
            AUTOCONF_FILE="$OUTPUT/include/linux/autoconf.h"
        fi
    else
        if [ -f "$HEADERS/generated/autoconf.h" ]; then
            AUTOCONF_FILE="$HEADERS/generated/autoconf.h"
        else
            AUTOCONF_FILE="$HEADERS/linux/autoconf.h"
        fi
    fi

    test_xen

    if [ "$XEN_PRESENT" != "0" ]; then
        MACH_CFLAGS="-I$HEADERS/asm/mach-xen"
    fi

    SOURCE_HEADERS="$HEADERS"
    SOURCE_ARCH_HEADERS="$SOURCES/arch/$KERNEL_ARCH/include"
    OUTPUT_HEADERS="$OUTPUT/include"
    OUTPUT_ARCH_HEADERS="$OUTPUT/arch/$KERNEL_ARCH/include"

    # Look for mach- directories on this arch, and add it to the list of
    # includes if that platform is enabled in the configuration file, which
    # may have a definition like this:
    #   #define CONFIG_ARCH_<MACHUPPERCASE> 1
    for _mach_dir in `ls -1d $SOURCES/arch/$KERNEL_ARCH/mach-* 2>/dev/null`; do
        _mach=`echo $_mach_dir | \
            sed -e "s,$SOURCES/arch/$KERNEL_ARCH/mach-,," | \
            tr 'a-z' 'A-Z'`
        grep "CONFIG_ARCH_$_mach \+1" $AUTOCONF_FILE > /dev/null 2>&1
        if [ $? -eq 0 ]; then
            MACH_CFLAGS="$MACH_CFLAGS -I$_mach_dir/include"
        fi
    done

    if [ "$ARCH" = "arm" ]; then
        MACH_CFLAGS="$MACH_CFLAGS -D__LINUX_ARM_ARCH__=7"
    fi

    # Add the mach-default includes (only found on x86/older kernels)
    MACH_CFLAGS="$MACH_CFLAGS -I$SOURCE_HEADERS/asm-$KERNEL_ARCH/mach-default"
    MACH_CFLAGS="$MACH_CFLAGS -I$SOURCE_ARCH_HEADERS/asm/mach-default"

    CFLAGS="$BASE_CFLAGS $MACH_CFLAGS $OUTPUT_CFLAGS -include $AUTOCONF_FILE"
    CFLAGS="$CFLAGS -I$SOURCE_HEADERS"
    CFLAGS="$CFLAGS -I$SOURCE_HEADERS/uapi"
    CFLAGS="$CFLAGS -I$SOURCE_HEADERS/xen"
    CFLAGS="$CFLAGS -I$OUTPUT_HEADERS/generated/uapi"
    CFLAGS="$CFLAGS -I$SOURCE_ARCH_HEADERS"
    CFLAGS="$CFLAGS -I$SOURCE_ARCH_HEADERS/uapi"
    CFLAGS="$CFLAGS -I$OUTPUT_ARCH_HEADERS/generated"
    CFLAGS="$CFLAGS -I$OUTPUT_ARCH_HEADERS/generated/uapi"

    if [ -n "$BUILD_PARAMS" ]; then
        CFLAGS="$CFLAGS -D$BUILD_PARAMS"
    fi

    # Check if gcc supports asm goto and set CC_HAVE_ASM_GOTO if it does.
    # Older kernels perform this check and set this flag in Kbuild, and since
    # conftest.sh runs outside of Kbuild it ends up building without this flag.
    # Starting with commit e9666d10a5677a494260d60d1fa0b73cc7646eb3 this test
    # is done within Kconfig, and the preprocessor flag is no longer needed.

    GCC_GOTO_SH="$SOURCES/build/gcc-goto.sh"

    if [ -f "$GCC_GOTO_SH" ]; then
        # Newer versions of gcc-goto.sh don't print anything on success, but
        # this is okay, since it's no longer necessary to set CC_HAVE_ASM_GOTO
        # based on the output of those versions of gcc-goto.sh.
        if [ `/bin/sh "$GCC_GOTO_SH" "$CC"` = "y" ]; then
            CFLAGS="$CFLAGS -DCC_HAVE_ASM_GOTO"
        fi
    fi

    #
    # If CONFIG_HAVE_FENTRY is enabled and gcc supports -mfentry flags then set
    # CC_USING_FENTRY and add -mfentry into cflags.
    #
    # linux/ftrace.h file indirectly gets included into the conftest source and
    # fails to get compiled, because conftest.sh runs outside of Kbuild it ends
    # up building without -mfentry and CC_USING_FENTRY flags.
    #
    grep "CONFIG_HAVE_FENTRY \+1" $AUTOCONF_FILE > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "" > conftest$$.c

        $CC -mfentry -c -x c conftest$$.c > /dev/null 2>&1
        rm -f conftest$$.c

        if [ -f conftest$$.o ]; then
            rm -f conftest$$.o

            CFLAGS="$CFLAGS -mfentry -DCC_USING_FENTRY"
        fi
    fi
}

CONFTEST_PREAMBLE="#include \"conftest/headers.h\"
    #if defined(NV_LINUX_KCONFIG_H_PRESENT)
    #include <linux/kconfig.h>
    #endif
    #if defined(NV_GENERATED_AUTOCONF_H_PRESENT)
    #include <generated/autoconf.h>
    #else
    #include <linux/autoconf.h>
    #endif
    #if defined(CONFIG_XEN) && \
        defined(CONFIG_XEN_INTERFACE_VERSION) &&  !defined(__XEN_INTERFACE_VERSION__)
    #define __XEN_INTERFACE_VERSION__ CONFIG_XEN_INTERFACE_VERSION
    #endif"

test_configuration_option() {
    #
    # Check to see if the given configuration option is defined
    #

    get_configuration_option $1 >/dev/null 2>&1

    return $?

}

compile_check_conftest() {
    #
    # Compile the current conftest C file and check+output the result
    #
    CODE="$1"
    DEF="$2"
    VAL="$3"
    CAT="$4"

    echo "$CONFTEST_PREAMBLE
    $CODE" > conftest$$.c

    $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
    rm -f conftest$$.c

    if [ -f conftest$$.o ]; then
        rm -f conftest$$.o
        if [ "${CAT}" = "functions" ]; then
            #
            # The logic for "functions" compilation tests is inverted compared to
            # other compilation steps: if the function is present, the code
            # snippet will fail to compile because the function call won't match
            # the prototype. If the function is not present, the code snippet
            # will produce an object file with the function as an unresolved
            # symbol.
            #
            echo "#undef ${DEF}" | append_conftest "${CAT}"
        else
            echo "#define ${DEF} ${VAL}" | append_conftest "${CAT}"
        fi
        return
    else
        if [ "${CAT}" = "functions" ]; then
            echo "#define ${DEF} ${VAL}" | append_conftest "${CAT}"
        else
            echo "#undef ${DEF}" | append_conftest "${CAT}"
        fi
        return
    fi
}

export_symbol_present_conftest() {
    #
    # Check Module.symvers to see whether the given symbol is present.
    #

    SYMBOL="$1"
    TAB='	'

    if grep -e "${TAB}${SYMBOL}${TAB}.*${TAB}EXPORT_SYMBOL.*\$" \
               "$OUTPUT/Module.symvers" >/dev/null 2>&1; then
        echo "#define NV_IS_EXPORT_SYMBOL_PRESENT_$SYMBOL 1" |
            append_conftest "symbols"
    else
        # May be a false negative if Module.symvers is absent or incomplete,
        # or if the Module.symvers format changes.
        echo "#define NV_IS_EXPORT_SYMBOL_PRESENT_$SYMBOL 0" |
            append_conftest "symbols"
    fi
}

export_symbol_gpl_conftest() {
    #
    # Check Module.symvers to see whether the given symbol is present and its
    # export type is GPL-only (including deprecated GPL-only symbols).
    #

    SYMBOL="$1"
    TAB='	'

    if grep -e "${TAB}${SYMBOL}${TAB}.*${TAB}EXPORT_\(UNUSED_\)*SYMBOL_GPL\$" \
               "$OUTPUT/Module.symvers" >/dev/null 2>&1; then
        echo "#define NV_IS_EXPORT_SYMBOL_GPL_$SYMBOL 1" |
            append_conftest "symbols"
    else
        # May be a false negative if Module.symvers is absent or incomplete,
        # or if the Module.symvers format changes.
        echo "#define NV_IS_EXPORT_SYMBOL_GPL_$SYMBOL 0" |
            append_conftest "symbols"
    fi
}

get_configuration_option() {
    #
    # Print the value of given configuration option, if defined
    #
    RET=1
    OPTION=$1

    OLD_FILE="linux/autoconf.h"
    NEW_FILE="generated/autoconf.h"
    FILE=""

    if [ -f $HEADERS/$NEW_FILE -o -f $OUTPUT/include/$NEW_FILE ]; then
        FILE=$NEW_FILE
    elif [ -f $HEADERS/$OLD_FILE -o -f $OUTPUT/include/$OLD_FILE ]; then
        FILE=$OLD_FILE
    fi

    if [ -n "$FILE" ]; then
        #
        # We are looking at a configured source tree; verify
        # that its configuration includes the given option
        # via a compile check, and print the option's value.
        #

        if [ -f $HEADERS/$FILE ]; then
            INCLUDE_DIRECTORY=$HEADERS
        elif [ -f $OUTPUT/include/$FILE ]; then
            INCLUDE_DIRECTORY=$OUTPUT/include
        else
            return 1
        fi

        echo "#include <$FILE>
        #ifndef $OPTION
        #error $OPTION not defined!
        #endif

        $OPTION
        " > conftest$$.c

        $CC -E -P -I$INCLUDE_DIRECTORY -o conftest$$ conftest$$.c > /dev/null 2>&1

        if [ -e conftest$$ ]; then
            tr -d '\r\n\t ' < conftest$$
            RET=$?
        fi

        rm -f conftest$$.c conftest$$
    else
        CONFIG=$OUTPUT/.config
        if [ -f $CONFIG ] && grep "^$OPTION=" $CONFIG; then
            grep "^$OPTION=" $CONFIG | cut -f 2- -d "="
            RET=$?
        fi
    fi

    return $RET

}

compile_test() {
    case "$1" in
        set_memory_uc)
            #
            # Determine if the set_memory_uc() function is present.
            #
            CODE="
            #if defined(NV_ASM_SET_MEMORY_H_PRESENT)
            #if defined(NV_ASM_PGTABLE_TYPES_H_PRESENT)
            #include <asm/pgtable_types.h>
            #endif
            #include <asm/set_memory.h>
            #else
            #include <asm/cacheflush.h>
            #endif
            void conftest_set_memory_uc(void) {
                set_memory_uc();
            }"

            compile_check_conftest "$CODE" "NV_SET_MEMORY_UC_PRESENT" "" "functions"
        ;;

        set_memory_array_uc)
            #
            # Determine if the set_memory_array_uc() function is present.
            #
            CODE="
            #if defined(NV_ASM_SET_MEMORY_H_PRESENT)
            #if defined(NV_ASM_PGTABLE_TYPES_H_PRESENT)
            #include <asm/pgtable_types.h>
            #endif
            #include <asm/set_memory.h>
            #else
            #include <asm/cacheflush.h>
            #endif
            void conftest_set_memory_array_uc(void) {
                set_memory_array_uc();
            }"

            compile_check_conftest "$CODE" "NV_SET_MEMORY_ARRAY_UC_PRESENT" "" "functions"
        ;;

        sysfs_slab_unlink)
            #
            # Determine if the sysfs_slab_unlink() function is present.
            #
            # This test is useful to check for the presence a fix for the deferred
            # kmem_cache destroy feature (see nvbug: 2543505).
            #
            # Added by commit d50d82faa0c9 ("slub: fix failure when we delete and
            # create a slab cache") in 4.18 (2018-06-27).
            #
            CODE="
            #include <linux/slab.h>
            void conftest_sysfs_slab_unlink(void) {
                sysfs_slab_unlink();
            }"

            compile_check_conftest "$CODE" "NV_SYSFS_SLAB_UNLINK_PRESENT" "" "functions"
        ;;

        list_is_first)
            #
            # Determine if the list_is_first() function is present.
            #
            # Added by commit 0d29c2d43753 ("mm, compaction: Use free lists to quickly
            # locate a migration source -fix") in linux-next tree
            #
            CODE="
            #include <linux/list.h> 
            void conftest_list_is_first(void) {
                list_is_first();
            }"

            compile_check_conftest "$CODE" "NV_LIST_IS_FIRST_PRESENT" "" "functions"
        ;;

        set_pages_uc)
            #
            # Determine if the set_pages_uc() function is present.
            #
            CODE="
            #if defined(NV_ASM_SET_MEMORY_H_PRESENT)
            #if defined(NV_ASM_PGTABLE_TYPES_H_PRESENT)
            #include <asm/pgtable_types.h>
            #endif
            #include <asm/set_memory.h>
            #else
            #include <asm/cacheflush.h>
            #endif
            void conftest_set_pages_uc(void) {
                set_pages_uc();
            }"

            compile_check_conftest "$CODE" "NV_SET_PAGES_UC_PRESENT" "" "functions"
        ;;

        outer_flush_all)
            #
            # Determine if the outer_cache_fns struct has flush_all member.
            #
            CODE="
            #include <asm/outercache.h>
            int conftest_outer_flush_all(void) {
                return offsetof(struct outer_cache_fns, flush_all);
            }"

            compile_check_conftest "$CODE" "NV_OUTER_FLUSH_ALL_PRESENT" "" "types"
        ;;

        change_page_attr)
            #
            # Determine if the change_page_attr() function is
            # present.
            #
            CODE="
            #include <linux/version.h>
            #include <linux/utsname.h>
            #include <linux/mm.h>
            #include <asm/cacheflush.h>
            void conftest_change_page_attr(void) {
                change_page_attr();
            }"

            compile_check_conftest "$CODE" "NV_CHANGE_PAGE_ATTR_PRESENT" "" "functions"
        ;;

        pci_get_class)
            #
            # Determine if the pci_get_class() function is
            # present.
            #
            CODE="
            #include <linux/pci.h>
            void conftest_pci_get_class(void) {
                pci_get_class();
            }"

            compile_check_conftest "$CODE" "NV_PCI_GET_CLASS_PRESENT" "" "functions"
        ;;

        pci_get_domain_bus_and_slot)
            #
            # Determine if the pci_get_domain_bus_and_slot() function
            # is present.
            #
            CODE="
            #include <linux/pci.h>
            void conftest_pci_get_domain_bus_and_slot(void) {
                pci_get_domain_bus_and_slot();
            }"

            compile_check_conftest "$CODE" "NV_PCI_GET_DOMAIN_BUS_AND_SLOT_PRESENT" "" "functions"
        ;;

        pci_save_state)
            #
            # Determine the number of arguments of pci_(save|restore)_state().
            # The explicit buffer argument is only present on 2.6.9. Assume the
            # interface is always present.
            #
            echo "$CONFTEST_PREAMBLE
            #include <linux/pci.h>
            void conftest_pci_save_state(void) {
                pci_save_state(NULL);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#define NV_PCI_SAVE_STATE_ARGUMENT_COUNT 1" | append_conftest "functions"
                rm -f conftest$$.o
                return
            else
                echo "#define NV_PCI_SAVE_STATE_ARGUMENT_COUNT 2" | append_conftest "functions"
                return
            fi
        ;;

        pci_bus_address)
            #
            # Determine if the pci_bus_address() function is
            # present.
            #
            CODE="
            #include <linux/pci.h>
            void conftest_pci_bus_address(void) {
                pci_bus_address();
            }"

            compile_check_conftest "$CODE" "NV_PCI_BUS_ADDRESS_PRESENT" "" "functions"
        ;;

        remap_pfn_range)
            #
            # Determine if the remap_pfn_range() function is
            # present.
            #
            CODE="
            #include <linux/mm.h>
            void conftest_remap_pfn_range(void) {
                remap_pfn_range();
            }"

            compile_check_conftest "$CODE" "NV_REMAP_PFN_RANGE_PRESENT" "" "functions"
        ;;

        hash__remap_4k_pfn)
            #
            # Determine if the hash__remap_4k_pfn() function is
            # present.
            # hash__remap_4k_pfn was added by this commit:
            # 2016-04-29  6cc1a0ee4ce29ad1cbdc622db6f9bc16d3056067
            #
            CODE="
            #if defined(NV_ASM_BOOK3S_64_HASH_64K_H_PRESENT)
            #include <linux/mm.h>
            #include <asm/book3s/64/hash-64k.h>
            #endif
            void conftest_hash__remap_4k_pfn(void) {
                hash__remap_4k_pfn();
            }"

            compile_check_conftest "$CODE" "NV_HASH__REMAP_4K_PFN_PRESENT" "" "functions"
        ;;

        follow_pfn)
            #
            # Determine if the follow_pfn() function is
            # present.
            #
            CODE="
            #include <linux/mm.h>
            void conftest_follow_pfn(void) {
                follow_pfn();
            }"

            compile_check_conftest "$CODE" "NV_FOLLOW_PFN_PRESENT" "" "functions"
        ;;

        i2c_adapter)
            #
            # Determine if the 'i2c_adapter' structure has the
            # client_register() field.
            #
            CODE="
            #include <linux/i2c.h>
            int conftest_i2c_adapter(void) {
                return offsetof(struct i2c_adapter, client_register);
            }"

            compile_check_conftest "$CODE" "NV_I2C_ADAPTER_HAS_CLIENT_REGISTER" "" "types"
        ;;

        pm_message_t)
            #
            # Determine if the 'pm_message_t' data type is present
            # and if it as an 'event' member.
            #
            echo "$CONFTEST_PREAMBLE
            #include <linux/pm.h>
            void conftest_pm_message_t(pm_message_t state) {
                pm_message_t *p = &state;
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#define NV_PM_MESSAGE_T_PRESENT" | append_conftest "types"
                rm -f conftest$$.o
            else
                echo "#undef NV_PM_MESSAGE_T_PRESENT" | append_conftest "types"
                echo "#undef NV_PM_MESSAGE_T_HAS_EVENT" | append_conftest "types"
                return
            fi

            echo "$CONFTEST_PREAMBLE
            #include <linux/pm.h>  
            int conftest_pm_message_t(void) {
                return offsetof(pm_message_t, event);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#define NV_PM_MESSAGE_T_HAS_EVENT" | append_conftest "types"
                rm -f conftest$$.o
                return
            else
                echo "#undef NV_PM_MESSAGE_T_HAS_EVENT" | append_conftest "types"
                return
            fi
        ;;

        pci_choose_state)
            #
            # Determine if the pci_choose_state() function is
            # present.
            #
            CODE="
            #include <linux/pci.h>
            void conftest_pci_choose_state(void) {
                pci_choose_state();
            }"

            compile_check_conftest "$CODE" "NV_PCI_CHOOSE_STATE_PRESENT" "" "functions"
        ;;

        vm_insert_page)
            #
            # Determine if the vm_insert_page() function is
            # present.
            #
            CODE="
            #include <linux/mm.h>
            void conftest_vm_insert_page(void) {
                vm_insert_page();
            }"

            compile_check_conftest "$CODE" "NV_VM_INSERT_PAGE_PRESENT" "" "functions"
        ;;

        irq_handler_t)
            #
            # Determine if the 'irq_handler_t' type is present and
            # if it takes a 'struct ptregs *' argument.
            #
            echo "$CONFTEST_PREAMBLE
            #include <linux/interrupt.h>
            irq_handler_t conftest_isr;
            " > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ ! -f conftest$$.o ]; then
                echo "#undef NV_IRQ_HANDLER_T_PRESENT" | append_conftest "types"
                rm -f conftest$$.o
                return
            fi

            rm -f conftest$$.o

            echo "$CONFTEST_PREAMBLE
            #include <linux/interrupt.h>
            irq_handler_t conftest_isr;
            int conftest_irq_handler_t(int irq, void *arg) {
                return conftest_isr(irq, arg);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#define NV_IRQ_HANDLER_T_PRESENT" | append_conftest "types"
                echo "#define NV_IRQ_HANDLER_T_ARGUMENT_COUNT 2" | append_conftest "types"
                rm -f conftest$$.o
                return
            fi

            echo "$CONFTEST_PREAMBLE
            #include <linux/interrupt.h>
            irq_handler_t conftest_isr;
            int conftest_irq_handler_t(int irq, void *arg, struct pt_regs *regs) {
                return conftest_isr(irq, arg, regs);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#define NV_IRQ_HANDLER_T_PRESENT" | append_conftest "types"
                echo "#define NV_IRQ_HANDLER_T_ARGUMENT_COUNT 3" | append_conftest "types"
                rm -f conftest$$.o
                return
            else
                echo "#error irq_handler_t() conftest failed!" | append_conftest "types"
                return
            fi
        ;;

        request_threaded_irq)
            #
            # Determine if the request_threaded_irq() function is present.
            #
            # added:   2009-03-23  3aa551c9b4c40018f0e261a178e3d25478dc04a9
            #
            CODE="
            #include <linux/interrupt.h>
            int conftest_request_threaded_irq(void) {
                return request_threaded_irq();
            }"
            compile_check_conftest "$CODE" "NV_REQUEST_THREADED_IRQ_PRESENT" "" "functions"
        ;;

        acpi_device_ops)
            #
            # Determine if the 'acpi_device_ops' structure has
            # a match() member.
            #
            CODE="
            #include <linux/acpi.h>
            int conftest_acpi_device_ops(void) {
                return offsetof(struct acpi_device_ops, match);
            }"

            compile_check_conftest "$CODE" "NV_ACPI_DEVICE_OPS_HAS_MATCH" "" "types"
        ;;

        acpi_op_remove)
            #
            # Determine the number of arguments to pass to the
            # 'acpi_op_remove' routine.
            #

            echo "$CONFTEST_PREAMBLE
            #include <linux/acpi.h>

            acpi_op_remove conftest_op_remove_routine;

            int conftest_acpi_device_ops_remove(struct acpi_device *device) {
                return conftest_op_remove_routine(device);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#define NV_ACPI_DEVICE_OPS_REMOVE_ARGUMENT_COUNT 1" | append_conftest "types"
                return
            fi

            CODE="
            #include <linux/acpi.h>

            acpi_op_remove conftest_op_remove_routine;

            int conftest_acpi_device_ops_remove(struct acpi_device *device, int type) {
                return conftest_op_remove_routine(device, type);
            }"

            compile_check_conftest "$CODE" "NV_ACPI_DEVICE_OPS_REMOVE_ARGUMENT_COUNT" "2" "types"
        ;;

        acpi_device_id)
            #
            # Determine if the 'acpi_device_id' structure has 
            # a 'driver_data' member.
            #
            CODE="
            #include <linux/acpi.h>
            int conftest_acpi_device_id(void) {
                return offsetof(struct acpi_device_id, driver_data);
            }"

            compile_check_conftest "$CODE" "NV_ACPI_DEVICE_ID_HAS_DRIVER_DATA" "" "types"
        ;;

        acquire_console_sem)
            #
            # Determine if the acquire_console_sem() function
            # is present.
            #
            CODE="
            #include <linux/console.h>
            void conftest_acquire_console_sem(void) {
                acquire_console_sem(NULL);
            }"

            compile_check_conftest "$CODE" "NV_ACQUIRE_CONSOLE_SEM_PRESENT" "" "functions"
        ;;

        console_lock)
            #
            # Determine if the console_lock() function is present.
            #
            CODE="
            #include <linux/console.h>
            void conftest_console_lock(void) {
                console_lock(NULL);
            }"

            compile_check_conftest "$CODE" "NV_CONSOLE_LOCK_PRESENT" "" "functions"
        ;;

        kmem_cache_create)
            #
            # Determine if the kmem_cache_create() function is
            # present and how many arguments it takes.
            #
            echo "$CONFTEST_PREAMBLE
            #include <linux/slab.h>
            void conftest_kmem_cache_create(void) {
                kmem_cache_create();
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#undef NV_KMEM_CACHE_CREATE_PRESENT" | append_conftest "functions"
                return
            fi

            echo "$CONFTEST_PREAMBLE
            #include <linux/slab.h>
            void conftest_kmem_cache_create(void) {
                kmem_cache_create(NULL, 0, 0, 0L, NULL, NULL);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#define NV_KMEM_CACHE_CREATE_PRESENT" | append_conftest "functions"
                echo "#define NV_KMEM_CACHE_CREATE_ARGUMENT_COUNT 6" | append_conftest "functions"
                return
            fi

            echo "$CONFTEST_PREAMBLE
            #include <linux/slab.h>
            void conftest_kmem_cache_create(void) {
                kmem_cache_create(NULL, 0, 0, 0L, NULL);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#define NV_KMEM_CACHE_CREATE_PRESENT" | append_conftest "functions"
                echo "#define NV_KMEM_CACHE_CREATE_ARGUMENT_COUNT 5" | append_conftest "functions"
                return
            else
                echo "#error kmem_cache_create() conftest failed!" | append_conftest "functions"
            fi
        ;;

        smp_call_function)
            #
            # Determine if the smp_call_function() function is
            # present and how many arguments it takes.
            #
            echo "$CONFTEST_PREAMBLE
            #include <linux/smp.h>
            void conftest_smp_call_function(void) {
            #ifdef CONFIG_SMP
                smp_call_function();
            #endif
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#undef NV_SMP_CALL_FUNCTION_PRESENT" | append_conftest "functions"
                return
            fi

            echo "$CONFTEST_PREAMBLE
            #include <linux/smp.h>
            void conftest_smp_call_function(void) {
                smp_call_function(NULL, NULL, 0, 0);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#define NV_SMP_CALL_FUNCTION_PRESENT" | append_conftest "functions"
                echo "#define NV_SMP_CALL_FUNCTION_ARGUMENT_COUNT 4" | append_conftest "functions"
                return
            fi

            echo "$CONFTEST_PREAMBLE
            #include <linux/smp.h>
            void conftest_smp_call_function(void) {
                smp_call_function(NULL, NULL, 0);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#define NV_SMP_CALL_FUNCTION_PRESENT" | append_conftest "functions"
                echo "#define NV_SMP_CALL_FUNCTION_ARGUMENT_COUNT 3" | append_conftest "functions"
                return
            else
                echo "#error smp_call_function() conftest failed!" | append_conftest "functions"
            fi
        ;;

        on_each_cpu)
            #
            # Determine if the on_each_cpu() function is present
            # and how many arguments it takes.
            #
            echo "$CONFTEST_PREAMBLE
            #include <linux/smp.h>
            void conftest_on_each_cpu(void) {
            #ifdef CONFIG_SMP
                on_each_cpu();
            #endif
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#undef NV_ON_EACH_CPU_PRESENT" | append_conftest "functions"
                return
            fi

            echo "$CONFTEST_PREAMBLE
            #include <linux/smp.h>
            void conftest_on_each_cpu(void) {
                on_each_cpu(NULL, NULL, 0, 0);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#define NV_ON_EACH_CPU_PRESENT" | append_conftest "functions"
                echo "#define NV_ON_EACH_CPU_ARGUMENT_COUNT 4" | append_conftest "functions"
                return
            fi

            echo "$CONFTEST_PREAMBLE
            #include <linux/smp.h>
            void conftest_on_each_cpu(void) {
                on_each_cpu(NULL, NULL, 0);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#define NV_ON_EACH_CPU_PRESENT" | append_conftest "functions"
                echo "#define NV_ON_EACH_CPU_ARGUMENT_COUNT 3" | append_conftest "functions"
                return
            else
                echo "#error on_each_cpu() conftest failed!" | append_conftest "functions"
            fi
        ;;

        register_cpu_notifier)
            #
            # Determine if register_cpu_notifier() is present
            # 
            # register_cpu_notifier() was removed by the following commit
            #   2016 Dec 25: b272f732f888d4cf43c943a40c9aaa836f9b7431
            #
            CODE="
            #include <linux/cpu.h>
            void conftest_register_cpu_notifier(void) {
                register_cpu_notifier();
            }" > conftest$$.c
            compile_check_conftest "$CODE" "NV_REGISTER_CPU_NOTIFIER_PRESENT" "" "functions"
        ;;

        cpuhp_setup_state)
            #
            # Determine if cpuhp_setup_state() is present
            # 
            # cpuhp_setup_state() was added by the following commit
            #   2016 Feb 26: 5b7aa87e0482be768486e0c2277aa4122487eb9d 
            # 
            # It is used as a replacement for register_cpu_notifier
            CODE="
            #include <linux/cpu.h>
            void conftest_cpuhp_setup_state(void) {
                cpuhp_setup_state();
            }" > conftest$$.c
            compile_check_conftest "$CODE" "NV_CPUHP_SETUP_STATE_PRESENT" "" "functions"
        ;;

        acpi_evaluate_integer)
            #
            # Determine if the acpi_evaluate_integer() function is
            # present and the type of its 'data' argument.
            #

            echo "$CONFTEST_PREAMBLE
            #include <linux/acpi.h>
            acpi_status acpi_evaluate_integer(acpi_handle h, acpi_string s,
                struct acpi_object_list *l, unsigned long long *d) {
                return AE_OK;
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#define NV_ACPI_EVALUATE_INTEGER_PRESENT" | append_conftest "functions"
                echo "typedef unsigned long long nv_acpi_integer_t;" | append_conftest "functions"
                return
            fi

            echo "$CONFTEST_PREAMBLE
            #include <linux/acpi.h>
            acpi_status acpi_evaluate_integer(acpi_handle h, acpi_string s,
                struct acpi_object_list *l, unsigned long *d) {
                return AE_OK;
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#define NV_ACPI_EVALUATE_INTEGER_PRESENT" | append_conftest "functions"
                echo "typedef unsigned long nv_acpi_integer_t;" | append_conftest "functions"
                return
            else
                #
                # We can't report a compile test failure here because
                # this is a catch-all for both kernels that don't
                # have acpi_evaluate_integer() and kernels that have
                # broken header files that make it impossible to
                # tell if the function is present.
                #
                echo "#undef NV_ACPI_EVALUATE_INTEGER_PRESENT" | append_conftest "functions"
                echo "typedef unsigned long nv_acpi_integer_t;" | append_conftest "functions"
            fi
        ;;

        acpi_walk_namespace)
            #
            # Determine if the acpi_walk_namespace() function is present
            # and how many arguments it takes.
            #
            echo "$CONFTEST_PREAMBLE
            #include <linux/acpi.h>
            void conftest_acpi_walk_namespace(void) {
                acpi_walk_namespace();
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#undef NV_ACPI_WALK_NAMESPACE_PRESENT" | append_conftest "functions"
                return
            fi

            echo "$CONFTEST_PREAMBLE
            #include <linux/acpi.h>
            void conftest_acpi_walk_namespace(void) {
                acpi_walk_namespace(0, NULL, 0, NULL, NULL, NULL, NULL);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#define NV_ACPI_WALK_NAMESPACE_PRESENT" | append_conftest "functions"
                echo "#define NV_ACPI_WALK_NAMESPACE_ARGUMENT_COUNT 7" | append_conftest "functions"
                return
            fi

            echo "$CONFTEST_PREAMBLE
            #include <linux/acpi.h>
            void conftest_acpi_walk_namespace(void) {
                acpi_walk_namespace(0, NULL, 0, NULL, NULL, NULL);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#define NV_ACPI_WALK_NAMESPACE_PRESENT" | append_conftest "functions"
                echo "#define NV_ACPI_WALK_NAMESPACE_ARGUMENT_COUNT 6" | append_conftest "functions"
                return
            else
                echo "#error acpi_walk_namespace() conftest failed!" | append_conftest "functions"
            fi
        ;;

        ioremap_cache)
            #
            # Determine if the ioremap_cache() function is present.
            #
            CODE="
            #include <asm/io.h>
            void conftest_ioremap_cache(void) {
                ioremap_cache();
            }"

            compile_check_conftest "$CODE" "NV_IOREMAP_CACHE_PRESENT" "" "functions"
        ;;

        ioremap_nocache)
            #
            # Determine if the ioremap_nocache() function is present.
            #
            CODE="
            #include <asm/io.h>
            void conftest_ioremap_nocache(void) {
                ioremap_nocache();
            }"

            compile_check_conftest "$CODE" "NV_IOREMAP_NOCACHE_PRESENT" "" "functions"
        ;;

        ioremap_wc)
            #
            # Determine if the ioremap_wc() function is present.
            #
            CODE="
            #include <asm/io.h>
            void conftest_ioremap_wc(void) {
                ioremap_wc();
            }"

            compile_check_conftest "$CODE" "NV_IOREMAP_WC_PRESENT" "" "functions"
        ;;

        proc_dir_entry)
            #
            # Determine if the 'proc_dir_entry' structure has 
            # an 'owner' member.
            #
            CODE="
            #include <linux/proc_fs.h>
            int conftest_proc_dir_entry(void) {
                return offsetof(struct proc_dir_entry, owner);
            }"

            compile_check_conftest "$CODE" "NV_PROC_DIR_ENTRY_HAS_OWNER" "" "types"
        ;;

      INIT_WORK)
            #
            # Determine how many arguments the INIT_WORK() macro
            # takes.
            #
            echo "$CONFTEST_PREAMBLE
            #include <linux/workqueue.h>
            void conftest_INIT_WORK(void) {
                INIT_WORK();
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#undef NV_INIT_WORK_PRESENT" | append_conftest "macros"
                rm -f conftest$$.o
                return
            fi

            echo "$CONFTEST_PREAMBLE
            #include <linux/workqueue.h>
            void conftest_INIT_WORK(void) {
                INIT_WORK((struct work_struct *)NULL, NULL, NULL);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#define NV_INIT_WORK_PRESENT" | append_conftest "macros"
                echo "#define NV_INIT_WORK_ARGUMENT_COUNT 3" | append_conftest "macros"
                rm -f conftest$$.o
                return
            fi

            echo "$CONFTEST_PREAMBLE
            #include <linux/workqueue.h>
            void conftest_INIT_WORK(void) {
                INIT_WORK((struct work_struct *)NULL, NULL);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#define NV_INIT_WORK_PRESENT" | append_conftest "macros"
                echo "#define NV_INIT_WORK_ARGUMENT_COUNT 2" | append_conftest "macros"
                rm -f conftest$$.o
                return
            else
                echo "#error INIT_WORK() conftest failed!" | append_conftest "macros"
                return
            fi
        ;;

      dma_mapping_error)
            #
            # Determine how many arguments dma_mapping_error()
            # takes.
            #
            echo "$CONFTEST_PREAMBLE
            #include <linux/dma-mapping.h>
            int conftest_dma_mapping_error(void) {
                return dma_mapping_error(NULL, 0);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#define NV_DMA_MAPPING_ERROR_ARGUMENT_COUNT 2" | append_conftest "functions"
                rm -f conftest$$.o
                return
            fi

            echo "$CONFTEST_PREAMBLE
            #include <linux/dma-mapping.h>
            int conftest_dma_mapping_error(void) {
                return dma_mapping_error(0);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#define NV_DMA_MAPPING_ERROR_ARGUMENT_COUNT 1" | append_conftest "functions"
                rm -f conftest$$.o
                return
            else
                echo "#error dma_mapping_error() conftest failed!" | append_conftest "functions"
                return
            fi
        ;;

        scatterlist)
            #
            # Determine if the 'scatterlist' structure has
            # a 'page_link' member.
            #
            CODE="
            #include <linux/types.h>
            #include <linux/scatterlist.h>
            int conftest_scatterlist(void) {
                return offsetof(struct scatterlist, page_link);
            }"

            compile_check_conftest "$CODE" "NV_SCATTERLIST_HAS_PAGE_LINK" "" "types"
        ;;

        pci_domain_nr)
            #
            # Determine if the pci_domain_nr() function is present.
            #
            CODE="
            #include <linux/types.h>
            #include <linux/pci.h>
            int conftest_pci_domain_nr(struct pci_dev *dev) {
                return pci_domain_nr();
            }"

            compile_check_conftest "$CODE" "NV_PCI_DOMAIN_NR_PRESENT" "" "functions"
        ;;

        file_operations)
            #
            # Determine if the 'file_operations' structure has
            # 'ioctl', 'unlocked_ioctl' and 'compat_ioctl' fields.
            #
            CODE="
            #include <linux/fs.h>
            int conftest_file_operations(void) {
                return offsetof(struct file_operations, ioctl);
            }"

            compile_check_conftest "$CODE" "NV_FILE_OPERATIONS_HAS_IOCTL" "" "types"

            CODE="
            #include <linux/fs.h>
            int conftest_file_operations(void) {
                return offsetof(struct file_operations, unlocked_ioctl);
            }"

            compile_check_conftest "$CODE" "NV_FILE_OPERATIONS_HAS_UNLOCKED_IOCTL" "" "types"

            CODE="
            #include <linux/fs.h>
            int conftest_file_operations(void) {
                return offsetof(struct file_operations, compat_ioctl);
            }"

            compile_check_conftest "$CODE" "NV_FILE_OPERATIONS_HAS_COMPAT_IOCTL" "" "types"
        ;;

        sg_table)
            #
            # Determine if the struct sg_table type is present.
            #
            CODE="
            #include <linux/scatterlist.h>
            struct sg_table conftest_sg_table;
            "

            compile_check_conftest "$CODE" "NV_SG_TABLE_PRESENT" "" "types"
        ;;

        sg_alloc_table)
            #
            # Determine if include/linux/scatterlist.h exists and which table
            # allocation functions are present if so.
            #
            echo "$CONFTEST_PREAMBLE
            #include <linux/scatterlist.h>
            void conftest_sg_alloc_table(void) {
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ ! -f conftest$$.o ]; then
                echo "#undef NV_SG_ALLOC_TABLE_PRESENT" | append_conftest "functions"
                echo "#undef NV_SG_ALLOC_TABLE_FROM_PAGES_PRESENT" | append_conftest "functions"
                return
            fi
            
            rm -f conftest$$.o

            CODE="
            #include <linux/scatterlist.h>
            void conftest_sg_alloc_table(void) {
                sg_alloc_table();
            }"

            compile_check_conftest "$CODE" "NV_SG_ALLOC_TABLE_PRESENT" "" "functions"

            CODE="
            #include <linux/scatterlist.h>
            void conftest_sg_alloc_table_from_pages(void) {
                sg_alloc_table_from_pages();
            }"

            compile_check_conftest "$CODE" "NV_SG_ALLOC_TABLE_FROM_PAGES_PRESENT" "" "functions"
        ;;

        efi_enabled)
            #
            # Determine if the efi_enabled symbol is present, or if
            # the efi_enabled() function is present and how many
            # arguments it takes.
            #
            echo "$CONFTEST_PREAMBLE
            #if defined(NV_LINUX_EFI_H_PRESENT)
            #include <linux/efi.h> 
            #endif
            int conftest_efi_enabled(void) {
                return efi_enabled();
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#undef NV_EFI_ENABLED_PRESENT" | append_conftest "symbols"
                echo "#undef NV_EFI_ENABLED_PRESENT" | append_conftest "functions"
                rm -f conftest$$.o
                return
            fi

            echo "$CONFTEST_PREAMBLE
            #if defined(NV_LINUX_EFI_H_PRESENT)
            #include <linux/efi.h> 
            #endif
            int conftest_efi_enabled(void) {
                return efi_enabled(0);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#define NV_EFI_ENABLED_PRESENT" | append_conftest "functions"
                echo "#define NV_EFI_ENABLED_ARGUMENT_COUNT 1" | append_conftest "functions"
                rm -f conftest$$.o
                return
            else
                echo "#define NV_EFI_ENABLED_PRESENT" | append_conftest "symbols"
                return
            fi
        ;;

        dom0_kernel_present)
            #
            # Add config parameter if running on DOM0.
            #
            if [ -n "$VGX_BUILD" ]; then
                echo "#define NV_DOM0_KERNEL_PRESENT" | append_conftest "generic"
            else
                echo "#undef NV_DOM0_KERNEL_PRESENT" | append_conftest "generic"
            fi
            return
        ;;

        nvidia_vgpu_kvm_build)
           #
           # Add config parameter if running on KVM host.
           #
           if [ -n "$VGX_KVM_BUILD" ]; then
                echo "#define NV_VGPU_KVM_BUILD" | append_conftest "generic"
            else
                echo "#undef NV_VGPU_KVM_BUILD" | append_conftest "generic"
            fi
            return
        ;;

        vfio_register_notifier)
            #
            # Check number of arguments required.
            #
            echo "$CONFTEST_PREAMBLE
            #include <linux/vfio.h>
            int conftest_vfio_register_notifier(void) {
                return vfio_register_notifier((struct device *) NULL, (struct notifier_block *) NULL);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#define NV_VFIO_NOTIFIER_ARGUMENT_COUNT 2" | append_conftest "functions"
                rm -f conftest$$.o
                return
            else
                echo "#define NV_VFIO_NOTIFIER_ARGUMENT_COUNT 4" | append_conftest "functions"
                return
            fi
        ;;

        vfio_info_add_capability_has_cap_type_id_arg)
            #
            # Check if vfio_info_add_capability() has cap_type_id field.
            # cap_type_id field was removed in commit:
            # 2017-12-12 dda01f787df9f9e46f1c0bf8aa11f246e300750d
            #
            CODE="
            #include <linux/vfio.h>
            int vfio_info_add_capability(struct vfio_info_cap *caps,
                                         int cap_type_id,
                                         void *cap_type) {
                return 0;
            }"

            compile_check_conftest "$CODE" "NV_VFIO_INFO_ADD_CAPABILITY_HAS_CAP_TYPE_ID_ARGS" "" "types"
        ;;

        nvidia_grid_build)
            if [ -n "$GRID_BUILD" ]; then
                echo "#define NV_GRID_BUILD" | append_conftest "generic"
            else
                echo "#undef NV_GRID_BUILD" | append_conftest "generic"
            fi
            return
        ;;

        vm_fault_present)
            #
            # Determine if the 'vm_fault' structure is present. The earlier
            # name for this struct was fault_data, and it was renamed to
            # vm_fault by:
            #
            #  2007-07-19  d0217ac04ca6591841e5665f518e38064f4e65bd
            #
            CODE="
            #include <linux/mm.h>
            int conftest_vm_fault_present(void) {
                return offsetof(struct vm_fault, flags);
            }"

            compile_check_conftest "$CODE" "NV_VM_FAULT_PRESENT" "" "types"
        ;;

        vm_fault_has_address)
            #
            # Determine if the 'vm_fault' structure has an 'address', or a
            # 'virtual_address' field. The .virtual_address field was
            # effectively renamed to .address, by these two commits:
            #
            # struct vm_fault: .address was added by:
            #  2016-12-14  82b0f8c39a3869b6fd2a10e180a862248736ec6f
            #
            # struct vm_fault: .virtual_address was removed by:
            #  2016-12-14  1a29d85eb0f19b7d8271923d8917d7b4f5540b3e
            #
            CODE="
            #include <linux/mm.h>
            int conftest_vm_fault_has_address(void) {
                return offsetof(struct vm_fault, address);
            }"

            compile_check_conftest "$CODE" "NV_VM_FAULT_HAS_ADDRESS" "" "types"
        ;;

    kmem_cache_has_kobj_remove_work)
            #
            # Determine if the 'kmem_cache' structure has 'kobj_remove_work'.
            #
            # 'kobj_remove_work' was added by commit 3b7b314053d02 ("slub: make
            # sysfs file removal asynchronous") in v4.12 (2017-06-23). This
            # commit introduced a race between kmem_cache destroy and create
            # which we need to workaround in our driver (see nvbug: 2543505).
            # Also see comment for sysfs_slab_unlink conftest.
            #
            CODE="
            #include <linux/mm.h>
            #include <linux/slab.h>
            #include <linux/slub_def.h>
            int conftest_kmem_cache_has_kobj_remove_work(void) {
                return offsetof(struct kmem_cache, kobj_remove_work);
            }"

            compile_check_conftest "$CODE" "NV_KMEM_CACHE_HAS_KOBJ_REMOVE_WORK" "" "types"
        ;;

        mdev_uuid)
            #
            # Determine if mdev_uuid() function is present or not
            #
            CODE="
            #include <linux/pci.h>
            #include <linux/mdev.h>
            void conftest_mdev_uuid() {
                mdev_uuid();
            }"

            compile_check_conftest "$CODE" "NV_MDEV_UUID_PRESENT" "" "functions"
        ;;

        mdev_dev)
            #
            # Determine if mdev_dev() function is present or not
            #
            CODE="
            #include <linux/pci.h>
            #include <linux/mdev.h>
            void conftest_mdev_dev() {
                mdev_dev();
            }"

            compile_check_conftest "$CODE" "NV_MDEV_DEV_PRESENT" "" "functions"
        ;;

        mdev_parent)
            #
            # Determine if the struct mdev_parent type is present.
            #
            CODE="
            #include <linux/pci.h>
            #include <linux/mdev.h>
            struct mdev_parent_ops conftest_mdev_parent;
            "

            compile_check_conftest "$CODE" "NV_MDEV_PARENT_OPS_STRUCT_PRESENT" "" "types"
        ;; 

        mdev_parent_dev)
            #
            # Determine if mdev_parent_dev() function is present or not
            #
            CODE="
            #include <linux/pci.h>
            #include <linux/mdev.h>
            void conftest_mdev_parent_dev() {
                mdev_parent_dev();
            }"

            compile_check_conftest "$CODE" "NV_MDEV_PARENT_DEV_PRESENT" "" "functions"
        ;;

        mdev_from_dev)
            #
            # Determine if mdev_from_dev() function is present or not.
            #
            # Added: 2016-12-30  99e3123e3d72616a829dad6d25aa005ef1ef9b13
            #
            CODE="
            #include <linux/pci.h>
            #include <linux/mdev.h>
            void conftest_mdev_from_dev() {
                mdev_from_dev();
            }"

            compile_check_conftest "$CODE" "NV_MDEV_FROM_DEV_PRESENT" "" "functions"
        ;;

        drm_available)
            #
            # Determine if the DRM subsystem is usable
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            #if defined(NV_DRM_DRM_DRV_H_PRESENT)
            #include <drm/drm_drv.h>
            #endif

            #if !defined(CONFIG_DRM) && !defined(CONFIG_DRM_MODULE)
            #error DRM not enabled
            #endif

            void conftest_drm_available(void) {
                struct drm_driver drv;

                /* 2013-10-02 1bb72532ac260a2d3982b40bdd4c936d779d0d16 */
                (void)drm_dev_alloc;

                /* 2013-10-02 c22f0ace1926da399d9a16dfaf09174c1b03594c */
                (void)drm_dev_register;

                /* 2013-10-02 c3a49737ef7db0bdd4fcf6cf0b7140a883e32b2a */
                (void)drm_dev_unregister;
            }"

            compile_check_conftest "$CODE" "NV_DRM_AVAILABLE" "" "generic"
        ;;

        drm_dev_unref)
            #
            # Determine if drm_dev_unref() is present.
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif
            void conftest_drm_dev_unref(void) {
                /*
                 * drm_dev_free() was added in:
                 *  2013-10-02 0dc8fe5985e01f238e7dc64ff1733cc0291811e8
                 * drm_dev_free() was renamed to drm_dev_unref() in:
                 *  2014-01-29 099d1c290e2ebc3b798961a6c177c3aef5f0b789
                 */
                drm_dev_unref();
            }"

            compile_check_conftest "$CODE" "NV_DRM_DEV_UNREF_PRESENT" "" "functions"
        ;;

        proc_create_data)
            #
            # Determine if the proc_create_data() function is present.
            #
            CODE="
            #include <linux/proc_fs.h>
            void conftest_proc_create_data(void) {
                proc_create_data();
            }"

            compile_check_conftest "$CODE" "NV_PROC_CREATE_DATA_PRESENT" "" "functions"
        ;;


        pde_data)
            #
            # Determine if the pde_data() function is present.
            #
            # The commit c28198889c15 removed the function
            # 'PDE_DATA()', and replaced it with 'pde_data()'
            # ("proc: remove PDE_DATA() completely") in v5.17-rc1. 
            #
            CODE="
            #include <linux/proc_fs.h>
            void conftest_pde_data(void) {
                pde_data();
            }"

            compile_check_conftest "$CODE" "NV_PDE_DATA_PRESENT" "" "functions"
        ;;

        PDE_DATA)
            #
            # Determine if the PDE_DATA() function is present.
            #
            CODE="
            #include <linux/proc_fs.h>
            void conftest_PDE_DATA(void) {
                PDE_DATA();
            }"

            compile_check_conftest "$CODE" "NV_PDE_DATA_UPPER_CASE_PRESENT" "" "functions"
        ;;

        get_num_physpages)
            #
            # Determine if the get_num_physpages() function is
            # present.
            #
            CODE="
            #include <linux/mm.h>
            void conftest_get_num_physpages(void) {
                get_num_physpages(NULL);
            }"

            compile_check_conftest "$CODE" "NV_GET_NUM_PHYSPAGES_PRESENT" "" "functions"
        ;;

        proc_remove)
            #
            # Determine if the proc_remove() function is present.
            #
            CODE="
            #include <linux/proc_fs.h>
            void conftest_proc_remove(void) {
                proc_remove();
            }"

            compile_check_conftest "$CODE" "NV_PROC_REMOVE_PRESENT" "" "functions"
        ;;

        vm_operations_struct)
            #
            # Determine if the 'vm_operations_struct' structure has
            # 'fault' and 'access' fields.
            #
            CODE="
            #include <linux/mm.h>
            int conftest_vm_operations_struct(void) {
                return offsetof(struct vm_operations_struct, fault);
            }"

            compile_check_conftest "$CODE" "NV_VM_OPERATIONS_STRUCT_HAS_FAULT" "" "types"

            CODE="
            #include <linux/mm.h>
            int conftest_vm_operations_struct(void) {
                return offsetof(struct vm_operations_struct, access);
            }"

            compile_check_conftest "$CODE" "NV_VM_OPERATIONS_STRUCT_HAS_ACCESS" "" "types"
        ;;

        fault_flags)
            # Determine if the FAULT_FLAG_WRITE is defined
            CODE="
            #include <linux/mm.h>
            void conftest_fault_flags(void) {
                int flag = FAULT_FLAG_WRITE;
            }"

            compile_check_conftest "$CODE" "NV_FAULT_FLAG_PRESENT" "" "types"
        ;;

        atomic_long_type)
            # Determine if atomic_long_t and associated functions are defined
            # Added in 2.6.16 2006-01-06 d3cb487149bd706aa6aeb02042332a450978dc1c
            CODE="
            #include <asm/atomic.h>
            void conftest_atomic_long(void) {
                atomic_long_t data;
                atomic_long_read(&data);
                atomic_long_set(&data, 0);
                atomic_long_inc(&data);
            }"

            compile_check_conftest "$CODE" "NV_ATOMIC_LONG_PRESENT" "" "types"
        ;;

        atomic64_type)
            # Determine if atomic64_t and associated functions are defined
            CODE="
            #include <asm/atomic.h>
            void conftest_atomic64(void) {
                atomic64_t data;
                atomic64_read(&data);
                atomic64_set(&data, 0);
                atomic64_inc(&data);
            }"

            compile_check_conftest "$CODE" "NV_ATOMIC64_PRESENT" "" "types"
        ;;

        task_struct)
            #
            # Determine if the 'task_struct' structure has
            # a 'cred' field.
            #
            CODE="
            #include <linux/sched.h>
            int conftest_task_struct(void) {
                return offsetof(struct task_struct, cred);
            }"

            compile_check_conftest "$CODE" "NV_TASK_STRUCT_HAS_CRED" "" "types"
        ;;

        backing_dev_info)
            #
            # Determine if the 'address_space' structure has
            # a 'backing_dev_info' field.
            #
            CODE="
            #include <linux/fs.h>
            int conftest_backing_dev_info(void) {
                return offsetof(struct address_space, backing_dev_info);
            }"

            compile_check_conftest "$CODE" "NV_ADDRESS_SPACE_HAS_BACKING_DEV_INFO" "" "types"
        ;;

        address_space)
            #
            # Determine if the 'address_space' structure has
            # a 'tree_lock' field of type rwlock_t.
            #
            CODE="
            #include <linux/fs.h>
            int conftest_address_space(void) {
                struct address_space as;
                rwlock_init(&as.tree_lock);
                return offsetof(struct address_space, tree_lock);
            }"

            compile_check_conftest "$CODE" "NV_ADDRESS_SPACE_HAS_RWLOCK_TREE_LOCK" "" "types"
        ;;

        address_space_init_once)
            #
            # Determine if address_space_init_once is present.
            #
            CODE="
            #include <linux/fs.h>
            void conftest_address_space_init_once(void) {
                address_space_init_once();
            }"

            compile_check_conftest "$CODE" "NV_ADDRESS_SPACE_INIT_ONCE_PRESENT" "" "functions"
        ;;

        kbasename)
            #
            # Determine if the kbasename() function is present.
            #
            CODE="
            #include <linux/string.h>
            void conftest_kbasename(void) {
                kbasename();
            }"

            compile_check_conftest "$CODE" "NV_KBASENAME_PRESENT" "" "functions"
        ;;

        fatal_signal_pending)
            #
            # Determine if fatal_signal_pending is present.
            #
            CODE="
            #if defined(NV_LINUX_SCHED_SIGNAL_H_PRESENT)
            #include <linux/sched/signal.h>
            #else
            #include <linux/sched.h>
            #endif
            void conftest_fatal_signal_pending(void) {
                fatal_signal_pending();
            }"

            compile_check_conftest "$CODE" "NV_FATAL_SIGNAL_PENDING_PRESENT" "" "functions"
        ;;

        kuid_t)
            #
            # Determine if the 'kuid_t' type is present.
            #
            CODE="
            #include <linux/sched.h>
            kuid_t conftest_kuid_t;
            "

            compile_check_conftest "$CODE" "NV_KUID_T_PRESENT" "" "types"
        ;;

        pm_vt_switch_required)
            #
            # Determine if the pm_vt_switch_required() function is present.
            #
            CODE="
            #include <linux/pm.h>
            void conftest_pm_vt_switch_required(void) {
                pm_vt_switch_required();
            }"

            compile_check_conftest "$CODE" "NV_PM_VT_SWITCH_REQUIRED_PRESENT" "" "functions"
        ;;
        
        list_cut_position)
            #
            # Determine if the list_cut_position() function is present.
            #
            CODE="
            #include <linux/list.h>
            void conftest_list_cut_position(void) {
                list_cut_position();
            }"

            compile_check_conftest "$CODE" "NV_LIST_CUT_POSITION_PRESENT" "" "functions"
        ;;

        file_inode)
            #
            # Determine if the 'file' structure has
            # a 'f_inode' field.
            #
            CODE="
            #include <linux/fs.h>
            int conftest_file_inode(void) {
                return offsetof(struct file, f_inode);
            }"

            compile_check_conftest "$CODE" "NV_FILE_HAS_INODE" "" "types"
        ;;

        xen_ioemu_inject_msi)
            #
            # Determine if the xen_ioemu_inject_msi() function is present.
            #
            CODE="
            #if defined(NV_XEN_IOEMU_H_PRESENT)
            #include <linux/kernel.h>
            #include <xen/interface/xen.h>
            #include <xen/hvm.h>
            #include <xen/ioemu.h>
            #endif
            void conftest_xen_ioemu_inject_msi(void) {
                xen_ioemu_inject_msi();
            }"

            compile_check_conftest "$CODE" "NV_XEN_IOEMU_INJECT_MSI" "" "functions"
        ;; 

        phys_to_dma)
            #
            # Determine if the phys_to_dma function is present.
            #
            CODE="
            #include <linux/dma-mapping.h>
            void conftest_phys_to_dma(void) {
                phys_to_dma();
            }"

            compile_check_conftest "$CODE" "NV_PHYS_TO_DMA_PRESENT" "" "functions"
        ;;

        dma_ops)
            #
            # Determine if the 'dma_ops' structure is present.
            #
            CODE="
            #include <linux/dma-mapping.h>
            void conftest_dma_ops(void) {
                (void)dma_ops;
            }"

            compile_check_conftest "$CODE" "NV_DMA_OPS_PRESENT" "" "symbols"
        ;;

        swiotlb_dma_ops)
            #
            # Determine if the 'swiotlb_dma_ops' structure is present.
            # It does not exist on all architectures.
            #
            CODE="
            #include <linux/dma-mapping.h>
            void conftest_dma_ops(void) {
                (void)swiotlb_dma_ops;
            }"

            compile_check_conftest "$CODE" "NV_SWIOTLB_DMA_OPS_PRESENT" "" "symbols"
        ;;

        dma_map_ops)
            #
            # Determine if the 'struct dma_map_ops' type is present.
            #
            # Commit 0a0f0d8be76d ("dma-mapping: split <linux/dma-mapping.h>")
            # in v5.10-rc1 (2020-09-22), moved 'struct dma_map_ops'
            # type from <linux/dma-mapping.h> to <linux/dma-map-ops.h>.
            #
            CODE="
            #if defined(NV_LINUX_DMA_MAP_OPS_H_PRESENT)
            #include <linux/dma-map-ops.h>
            #else
            #include <linux/dma-mapping.h>
            #endif
            void conftest_dma_map_ops(void) {
                struct dma_map_ops ops;
            }"

            compile_check_conftest "$CODE" "NV_DMA_MAP_OPS_PRESENT" "" "types"
        ;;
 
        get_dma_ops)
            #
            # Determine if the get_dma_ops() function is present.
            #
            # Commit 0a0f0d8be76d ("dma-mapping: split <linux/dma-mapping.h>")
            # in v5.10-rc1 (2020-09-22), moved get_dma_ops() function
            # prototype from <linux/dma-mapping.h> to <linux/dma-map-ops.h>.
            #
            CODE="
            #if defined(NV_LINUX_DMA_MAP_OPS_H_PRESENT)
            #include <linux/dma-map-ops.h>
            #else
            #include <linux/dma-mapping.h>
            #endif
            void conftest_get_dma_ops(void) {
                get_dma_ops();
            }"

            compile_check_conftest "$CODE" "NV_GET_DMA_OPS_PRESENT" "" "functions"
        ;;

        noncoherent_swiotlb_dma_ops)
            #
            # Determine if the 'noncoherent_swiotlb_dma_ops' symbol is present.
            #
            CODE="
            #include <linux/dma-mapping.h>
            void conftest_noncoherent_swiotlb_dma_ops(void) {
                (void)noncoherent_swiotlb_dma_ops;
            }"

            compile_check_conftest "$CODE" "NV_NONCOHERENT_SWIOTLB_DMA_OPS_PRESENT" "" "symbols"
        ;;

        dma_map_resource)
            #
            # Determine if the dma_map_resource() function is present.
            #
            # dma_map_resource() was added by:
            #   2016-08-10  6f3d87968f9c8b529bc81eff5a1f45e92553493d
            #
            CODE="
            #include <linux/dma-mapping.h>
            void conftest_dma_map_resource(void) {
                dma_map_resource();
            }"

            compile_check_conftest "$CODE" "NV_DMA_MAP_RESOURCE_PRESENT" "" "functions"
        ;;

        write_cr4)
            #
            # Determine if the write_cr4() function is present.
            #
            CODE="
            #include <asm/processor.h>
            void conftest_write_cr4(void) {
                write_cr4();
            }"

            compile_check_conftest "$CODE" "NV_WRITE_CR4_PRESENT" "" "functions"
        ;;

        of_get_property)
            #
            # Determine if the of_get_property function is present.
            #
            CODE="
            #if defined(NV_LINUX_OF_H_PRESENT)
            #include <linux/of.h>
            #endif
            void conftest_of_get_property() {
                of_get_property();
            }"

            compile_check_conftest "$CODE" "NV_OF_GET_PROPERTY_PRESENT" "" "functions"
        ;;

        of_find_node_by_phandle)
            #
            # Determine if the of_find_node_by_phandle function is present.
            #
            CODE="
            #if defined(NV_LINUX_OF_H_PRESENT)
            #include <linux/of.h>
            #endif
            void conftest_of_find_node_by_phandle() {
                of_find_node_by_phandle();
            }"

            compile_check_conftest "$CODE" "NV_OF_FIND_NODE_BY_PHANDLE_PRESENT" "" "functions"
        ;;

        of_node_to_nid)
            #
            # Determine if of_node_to_nid is present
            #
            CODE="
            #include <linux/version.h>
            #include <linux/utsname.h>
            #if defined(NV_LINUX_OF_H_PRESENT)
              #include <linux/of.h>
            #endif
            void conftest_of_node_to_nid() {
              of_node_to_nid();
            }"

            compile_check_conftest "$CODE" "NV_OF_NODE_TO_NID_PRESENT" "" "functions"
        ;;

        pnv_pci_get_npu_dev)
            #
            # Determine if the pnv_pci_get_npu_dev function is present.
            #
            CODE="
            #include <linux/pci.h>
            void conftest_pnv_pci_get_npu_dev() {
                pnv_pci_get_npu_dev();
            }"

            compile_check_conftest "$CODE" "NV_PNV_PCI_GET_NPU_DEV_PRESENT" "" "functions"
        ;;

        for_each_online_node)
            #
            # Determine if the for_each_online_node() function is present.
            #
            CODE="
            #include <linux/mm.h>
            void conftest_for_each_online_node() {
                for_each_online_node();
            }"

            compile_check_conftest "$CODE" "NV_FOR_EACH_ONLINE_NODE_PRESENT" "" "functions"
        ;;

        node_end_pfn)
            #
            # Determine if the node_end_pfn() function is present.
            #
            CODE="
            #include <linux/mm.h>
            void conftest_node_end_pfn() {
                node_end_pfn();
            }"

            compile_check_conftest "$CODE" "NV_NODE_END_PFN_PRESENT" "" "functions"
        ;;

        kernel_write)
            #
            # Determine if kernel_write function is present
            #
            CODE="
            #include <linux/fs.h>
            void conftest_kernel_write() {
                kernel_write();
            }"

            compile_check_conftest "$CODE" "NV_KERNEL_WRITE_PRESENT" "" "functions"
        ;;

        strnstr)
            #
            # Determine if strnstr function is present
            #
            CODE="
            #include <linux/string.h>
            void conftest_strnstr() {
                strnstr();
            }"

            compile_check_conftest "$CODE" "NV_STRNSTR_PRESENT" "" "functions"
        ;;

        iterate_dir)
            #
            # Determine if iterate_dir function is present
            #
            CODE="
            #include <linux/fs.h>
            void conftest_iterate_dir() {
                iterate_dir();
            }"

            compile_check_conftest "$CODE" "NV_ITERATE_DIR_PRESENT" "" "functions"
        ;;
        kstrtoull)
            #
            # Determine if kstrtoull function is present
            #
            CODE="
            #include <linux/kernel.h>
            void conftest_kstrtoull() {
                kstrtoull();
            }"

            compile_check_conftest "$CODE" "NV_KSTRTOULL_PRESENT" "" "functions"
        ;;

        drm_atomic_available)
            #
            # Determine if the DRM atomic modesetting subsystem is usable
            #
            # ("drm/atomic: Allow drivers to subclass drm_atomic_state, v3") in
            # v4.2 (2018-05-18).
            #
            # Make conftest more robust by adding test for
            # drm_atomic_set_mode_prop_for_crtc(), this function added by
            # commit 955f3c334f0f ("drm/atomic: Add MODE_ID property") in v4.2
            # (2015-05-25). If the DRM atomic modesetting subsystem is
            # back ported to Linux kernel older than v4.2, then commit
            # 955f3c334f0f must be back ported in order to get NVIDIA-DRM KMS
            # support.
            # Commit 72fdb40c1a4b ("drm: extract drm_atomic_uapi.c") in v4.20
            # (2018-09-05), moved drm_atomic_set_mode_prop_for_crtc() function
            # prototype from drm/drm_atomic.h to drm/drm_atomic_uapi.h.
            #
            echo "$CONFTEST_PREAMBLE
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif
            #include <drm/drm_atomic.h>
            #if !defined(CONFIG_DRM) && !defined(CONFIG_DRM_MODULE)
            #error DRM not enabled
            #endif
            void conftest_drm_atomic_modeset_available(void) {
                size_t a;

                /* 2015-05-18 036ef5733ba433760a3512bb5f7a155946e2df05 */
                a = offsetof(struct drm_mode_config_funcs, atomic_state_alloc);
            }" > conftest$$.c;

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o

                echo "$CONFTEST_PREAMBLE
                #if defined(NV_DRM_DRMP_H_PRESENT)
                #include <drm/drmP.h>
                #endif
                #include <drm/drm_atomic.h>
                #if defined(NV_DRM_DRM_ATOMIC_UAPI_H_PRESENT)
                #include <drm/drm_atomic_uapi.h>
                #endif
                void conftest_drm_atomic_set_mode_prop_for_crtc(void) {
                    drm_atomic_set_mode_prop_for_crtc();
                }" > conftest$$.c;

                $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
                rm -f conftest$$.c

                if [ -f conftest$$.o ]; then
                    rm -f conftest$$.o
                    echo "#undef NV_DRM_ATOMIC_MODESET_AVAILABLE" | append_conftest "generic"
                else
                    echo "#define NV_DRM_ATOMIC_MODESET_AVAILABLE" | append_conftest "generic"
                fi
            else
                echo "#undef NV_DRM_ATOMIC_MODESET_AVAILABLE" | append_conftest "generic"
            fi
        ;;

        drm_bus_present)
            #
            # Determine if the 'struct drm_bus' type is present.
            #
            # added:   2010-12-15  8410ea3b95d105a5be5db501656f44bbb91197c1
            # removed: 2014-08-29  c5786fe5f1c50941dbe27fc8b4aa1afee46ae893
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            void conftest_drm_bus_present(void) {
                struct drm_bus bus;
            }"

            compile_check_conftest "$CODE" "NV_DRM_BUS_PRESENT" "" "types"
        ;;

        drm_bus_has_bus_type)
            #
            # Determine if the 'drm_bus' structure has a 'bus_type' field.
            #
            # added:   2010-12-15  8410ea3b95d105a5be5db501656f44bbb91197c1
            # removed: 2013-11-03  42b21049fc26513ca8e732f47559b1525b04a992
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            int conftest_drm_bus_has_bus_type(void) {
                return offsetof(struct drm_bus, bus_type);
            }"

            compile_check_conftest "$CODE" "NV_DRM_BUS_HAS_BUS_TYPE" "" "types"
        ;;

        drm_bus_has_get_irq)
            #
            # Determine if the 'drm_bus' structure has a 'get_irq' field.
            #
            # added:   2010-12-15  8410ea3b95d105a5be5db501656f44bbb91197c1
            # removed: 2013-11-03  b2a21aa25a39837d06eb24a7f0fef1733f9843eb
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            int conftest_drm_bus_has_get_irq(void) {
                return offsetof(struct drm_bus, get_irq);
            }"

            compile_check_conftest "$CODE" "NV_DRM_BUS_HAS_GET_IRQ" "" "types"
        ;;

        drm_bus_has_get_name)
            #
            # Determine if the 'drm_bus' structure has a 'get_name' field.
            #
            # added:   2010-12-15  8410ea3b95d105a5be5db501656f44bbb91197c1
            # removed: 2013-11-03  9de1b51f1fae6476155350a0670dc637c762e718
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            int conftest_drm_bus_has_get_name(void) {
                return offsetof(struct drm_bus, get_name);
            }"

            compile_check_conftest "$CODE" "NV_DRM_BUS_HAS_GET_NAME" "" "types"
        ;;

        drm_driver_has_device_list)
            #
            # Determine if the 'drm_driver' structure has a 'device_list' field.
            #
            # Renamed from device_list to legacy_device_list by commit
            # b3f2333de8e8 ("drm: restrict the device list for shadow
            # attached drivers") in v3.14 (2013-12-11)
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            #if defined(NV_DRM_DRM_DRV_H_PRESENT)
            #include <drm/drm_drv.h>
            #endif

            int conftest_drm_driver_has_device_list(void) {
                return offsetof(struct drm_driver, device_list);
            }"

            compile_check_conftest "$CODE" "NV_DRM_DRIVER_HAS_DEVICE_LIST" "" "types"
        ;;


        drm_driver_has_legacy_dev_list)
            #
            # Determine if the 'drm_driver' structure has a 'legacy_dev_list' field.
            #
            # drm_driver::device_list was added by:
            #   2008-11-28  e7f7ab45ebcb54fd5f814ea15ea079e079662f67
            # and then renamed to drm_driver::legacy_device_list by:
            #   2013-12-11  b3f2333de8e81b089262b26d52272911523e605f
            #
            # The commit 57bb1ee60340 ("drm: Compile out legacy chunks from
            # struct drm_device") compiles out the legacy chunks like
            # drm_driver::legacy_dev_list.
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            #if defined(NV_DRM_DRM_DRV_H_PRESENT)
            #include <drm/drm_drv.h>
            #endif

            int conftest_drm_driver_has_legacy_dev_list(void) {
                return offsetof(struct drm_driver, legacy_dev_list);
            }"

            compile_check_conftest "$CODE" "NV_DRM_DRIVER_HAS_LEGACY_DEV_LIST" "" "types"
        ;;

        jiffies_to_timespec)
            #
            # Determine if jiffies_to_timespec() is present
            #
            # removed by commit 751addac78b6
            # ("y2038: remove obsolete jiffies conversion functions")
            # in v5.6-rc1 (2019-12-13).
        CODE="
        #include <linux/jiffies.h>
        void conftest_jiffies_to_timespec(void){
            jiffies_to_timespec();
        }"
            compile_check_conftest "$CODE" "NV_JIFFIES_TO_TIMESPEC_PRESENT" "" "functions"
        ;;

        drm_init_function_args)
            #
            # Determine if these functions:
            #   drm_universal_plane_init()
            #   drm_crtc_init_with_planes()
            #   drm_encoder_init()
            # have a 'name' argument, which was added by these commits:
            #   drm_universal_plane_init:   2015-12-09  b0b3b7951114315d65398c27648705ca1c322faa
            #   drm_crtc_init_with_planes:  2015-12-09  f98828769c8838f526703ef180b3088a714af2f9
            #   drm_encoder_init:           2015-12-09  13a3d91f17a5f7ed2acd275d18b6acfdb131fb15
            #
            # Additionally determine whether drm_universal_plane_init() has a
            # 'format_modifiers' argument, which was added by:
            #   2017-07-23  e6fc3b68558e4c6d8d160b5daf2511b99afa8814
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            #if defined(NV_DRM_DRM_CRTC_H_PRESENT)
            #include <drm/drm_crtc.h>
            #endif

            int conftest_drm_crtc_init_with_planes_has_name_arg(void) {
                return
                    drm_crtc_init_with_planes(
                            NULL,  /* struct drm_device *dev */
                            NULL,  /* struct drm_crtc *crtc */
                            NULL,  /* struct drm_plane *primary */
                            NULL,  /* struct drm_plane *cursor */
                            NULL,  /* const struct drm_crtc_funcs *funcs */
                            NULL);  /* const char *name */
            }"

            compile_check_conftest "$CODE" "NV_DRM_CRTC_INIT_WITH_PLANES_HAS_NAME_ARG" "" "types"

            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            #if defined(NV_DRM_DRM_ENCODER_H_PRESENT)
            #include <drm/drm_encoder.h>
            #endif

            int conftest_drm_encoder_init_has_name_arg(void) {
                return
                    drm_encoder_init(
                            NULL,  /* struct drm_device *dev */
                            NULL,  /* struct drm_encoder *encoder */
                            NULL,  /* const struct drm_encoder_funcs *funcs */
                            DRM_MODE_ENCODER_NONE, /* int encoder_type */
                            NULL); /* const char *name */
            }"

            compile_check_conftest "$CODE" "NV_DRM_ENCODER_INIT_HAS_NAME_ARG" "" "types"

            echo "$CONFTEST_PREAMBLE
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            #if defined(NV_DRM_DRM_PLANE_H_PRESENT)
            #include <drm/drm_plane.h>
            #endif

            int conftest_drm_universal_plane_init_has_format_modifiers_arg(void) {
                return
                    drm_universal_plane_init(
                            NULL,  /* struct drm_device *dev */
                            NULL,  /* struct drm_plane *plane */
                            0,     /* unsigned long possible_crtcs */
                            NULL,  /* const struct drm_plane_funcs *funcs */
                            NULL,  /* const uint32_t *formats */
                            0,     /* unsigned int format_count */
                            NULL,  /* const uint64_t *format_modifiers */
                            DRM_PLANE_TYPE_PRIMARY,
                            NULL);  /* const char *name */
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o

                echo "#define NV_DRM_UNIVERSAL_PLANE_INIT_HAS_FORMAT_MODIFIERS_ARG" | append_conftest "types"
                echo "#define NV_DRM_UNIVERSAL_PLANE_INIT_HAS_NAME_ARG" | append_conftest "types"
            else
                echo "#undef NV_DRM_UNIVERSAL_PLANE_INIT_HAS_FORMAT_MODIFIERS_ARG" | append_conftest "types"

                echo "$CONFTEST_PREAMBLE
                #if defined(NV_DRM_DRMP_H_PRESENT)
                #include <drm/drmP.h>
                #endif

                #if defined(NV_DRM_DRM_PLANE_H_PRESENT)
                #include <drm/drm_plane.h>
                #endif

                int conftest_drm_universal_plane_init_has_name_arg(void) {
                    return
                        drm_universal_plane_init(
                                NULL,  /* struct drm_device *dev */
                                NULL,  /* struct drm_plane *plane */
                                0,     /* unsigned long possible_crtcs */
                                NULL,  /* const struct drm_plane_funcs *funcs */
                                NULL,  /* const uint32_t *formats */
                                0,     /* unsigned int format_count */
                                DRM_PLANE_TYPE_PRIMARY,
                                NULL);  /* const char *name */
                }" > conftest$$.c

                $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1

                if [ -f conftest$$.o ]; then
                    rm -f conftest$$.o

                    echo "#define NV_DRM_UNIVERSAL_PLANE_INIT_HAS_NAME_ARG" | append_conftest "types"
                else
                    echo "#undef NV_DRM_UNIVERSAL_PLANE_INIT_HAS_NAME_ARG" | append_conftest "types"
                fi
            fi

        ;;

        drm_mode_connector_list_update_has_merge_type_bits_arg)
            #
            # Detect if drm_mode_connector_list_update() has a
            # 'merge_type_bits' second argument.  This argument was
            # remove by:
            #   2015-12-03  6af3e6561243f167dabc03f732d27ff5365cd4a4
            #
            CODE="
            #include <drm/drmP.h>
            void conftest_drm_mode_connector_list_update_has_merge_type_bits_arg(void) {
                drm_mode_connector_list_update(
                    NULL,  /* struct drm_connector *connector */
                    true); /* bool merge_type_bits */
            }"

            compile_check_conftest "$CODE" "NV_DRM_MODE_CONNECTOR_LIST_UPDATE_HAS_MERGE_TYPE_BITS_ARG" "" "types"
        ;;

        vzalloc)
            #
            # Determine if the vzalloc function is present
            # Added in 2.6.37 2010-10-26 e1ca7788dec6773b1a2bce51b7141948f2b8bccf
            #
            CODE="
            #include <linux/vmalloc.h>
            void conftest_vzalloc() {
                vzalloc();
            }"

            compile_check_conftest "$CODE" "NV_VZALLOC_PRESENT" "" "functions"
        ;;

        drm_driver_has_set_busid)
            #
            # Determine if the drm_driver structure has a 'set_busid' callback
            # field.
            #
            # drm_driver::set_busid field were added by:
            #   2014-08-29  915b4d11b8b9e7b84ba4a4645b6cc7fbc0c071cf
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            int conftest_drm_driver_has_set_busid(void) {
                return offsetof(struct drm_driver, set_busid);
            }"

            compile_check_conftest "$CODE" "NV_DRM_DRIVER_HAS_SET_BUSID" "" "types"
        ;;

        drm_driver_has_gem_prime_res_obj)
            #
            # Determine if the drm_driver structure has a 'gem_prime_res_obj'
            # callback field.
            #
            # drm_driver::gem_prime_res_obj field was added by:
            #   2014-07-01  3aac4502fd3f80dcf7e65dbf6edd8676893c1f46
            #
            # Removed by commit 51c98747113e (drm/prime: Ditch
            # gem_prime_res_obj hook) in v5.4.
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            int conftest_drm_driver_has_gem_prime_res_obj(void) {
                return offsetof(struct drm_driver, gem_prime_res_obj);
            }"

            compile_check_conftest "$CODE" "NV_DRM_DRIVER_HAS_GEM_PRIME_RES_OBJ" "" "types"
        ;;

        drm_crtc_state_has_connectors_changed)
            #
            # Determine if the crtc_state has a 'connectors_changed' field.
            #
            # drm_crtc_state::connectors_changed was added by:
            #   2015-07-21  fc596660dd4e83f7f84e3cd7b25dc5e8e83000ef
            #
            CODE="
            #include <drm/drm_crtc.h>
            void conftest_drm_crtc_state_has_connectors_changed(void) {
                struct drm_crtc_state foo;
                (void)foo.connectors_changed;
            }"

            compile_check_conftest "$CODE" "NV_DRM_CRTC_STATE_HAS_CONNECTORS_CHANGED" "" "types"
        ;;

        drm_reinit_primary_mode_group)
            #
            # Determine if the function drm_reinit_primary_mode_group() is
            # present.
            #
            # drm_reinit_primary_mode_group was added by:
            #   2014-06-05  2390cd11bfbe8d2b1b28c4e0f01fe7e122f7196d
            # removed by commit:
            #   2015-07-09  3fdefa399e4644399ce3e74e65a75122d52dba6a
            #
            CODE="
            #if defined(NV_DRM_DRM_CRTC_H_PRESENT)
            #include <drm/drm_crtc.h>
            #endif
            void conftest_drm_reinit_primary_mode_group(void) {
                drm_reinit_primary_mode_group();
            }"

            compile_check_conftest "$CODE" "NV_DRM_REINIT_PRIMARY_MODE_GROUP_PRESENT" "" "functions"
        ;;

        wait_on_bit_lock_argument_count)
            #
            # Determine how many arguments wait_on_bit_lock takes.
            #
            #  wait_on_bit_lock changed by
            #    2014-07-07  743162013d40ca612b4cb53d3a200dff2d9ab26e
            #
            echo "$CONFTEST_PREAMBLE
            #include <linux/wait.h>
            void conftest_wait_on_bit_lock(void) {
                wait_on_bit_lock(NULL, 0, 0);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#define NV_WAIT_ON_BIT_LOCK_ARGUMENT_COUNT 3" | append_conftest "functions"
                return
            fi

            echo "$CONFTEST_PREAMBLE
            #include <linux/wait.h>
            void conftest_wait_on_bit_lock(void) {
                wait_on_bit_lock(NULL, 0, NULL, 0);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#define NV_WAIT_ON_BIT_LOCK_ARGUMENT_COUNT 4" | append_conftest "functions"
                return
            fi
            echo "#error wait_on_bit_lock() conftest failed!" | append_conftest "functions"
        ;;

        bitmap_clear)
            #
            # Determine if the bitmap_clear function is present
            # Added in 2.6.33 2009-12-15 c1a2a962a2ad103846e7950b4591471fabecece7
            #
            CODE="
            #include <linux/bitmap.h>
            void conftest_bitmap_clear() {
                bitmap_clear();
            }"

            compile_check_conftest "$CODE" "NV_BITMAP_CLEAR_PRESENT" "" "functions"
        ;;

        pci_stop_and_remove_bus_device)
            #
            # Determine if the pci_stop_and_remove_bus_device() function is present.
            # Added in 3.4-rc1 2012-02-25 210647af897af8ef2d00828aa2a6b1b42206aae6
            #
            CODE="
            #include <linux/types.h>
            #include <linux/pci.h>
            void conftest_pci_stop_and_remove_bus_device() {
                pci_stop_and_remove_bus_device();
            }"

            compile_check_conftest "$CODE" "NV_PCI_STOP_AND_REMOVE_BUS_DEVICE_PRESENT" "" "functions"
        ;;

        pci_remove_bus_device)
            #
            # Determine if the pci_remove_bus_device() function is present.
            # Added before Linux-2.6.12-rc2 2005-04-16
            #
            CODE="
            #include <linux/types.h>
            #include <linux/pci.h>
            void conftest_pci_remove_bus_device() {
                pci_remove_bus_device();
            }"

            compile_check_conftest "$CODE" "NV_PCI_REMOVE_BUS_DEVICE_PRESENT" "" "functions"
        ;;

        drm_atomic_set_mode_for_crtc)
            #
            # Determine if the function drm_atomic_set_mode_for_crtc() is
            # present.
            #
            # drm_atomic_set_mode_for_crtc() was added by:
            #   2015-05-26  819364da20fd914aba2fd03e95ee0467286752f5
            #
            CODE="
            #if defined(NV_DRM_DRM_ATOMIC_H_PRESENT)
            #include <drm/drm_atomic.h>
            #endif
            void conftest_drm_atomic_clean_old_fb(void) {
                drm_atomic_set_mode_for_crtc();
            }"

            compile_check_conftest "$CODE" "NV_DRM_ATOMIC_SET_MODE_FOR_CRTC" "" "functions"
        ;;

        drm_atomic_clean_old_fb)
            #
            # Determine if the function drm_atomic_clean_old_fb() is
            # present.
            #
            # drm_atomic_clean_old_fb() was added by:
            #   2015-11-11  0f45c26fc302c02b0576db37d4849baa53a2bb41
            #
            CODE="
            #if defined(NV_DRM_DRM_ATOMIC_H_PRESENT)
            #include <drm/drm_atomic.h>
            #endif
            void conftest_drm_atomic_clean_old_fb(void) {
                drm_atomic_clean_old_fb();
            }"

            compile_check_conftest "$CODE" "NV_DRM_ATOMIC_CLEAN_OLD_FB" "" "functions"
        ;;

        drm_helper_mode_fill_fb_struct | drm_helper_mode_fill_fb_struct_has_const_mode_cmd_arg)
            #
            # Determine if the drm_helper_mode_fill_fb_struct function takes
            # 'dev' argument.
            #
            # The drm_helper_mode_fill_fb_struct() has been updated to
            # take 'dev' parameter by:
            #   2016-12-14  a3f913ca98925d7e5bae725e9b2b38408215a695
            #
            echo "$CONFTEST_PREAMBLE
            #include <drm/drm_crtc_helper.h>
            void drm_helper_mode_fill_fb_struct(struct drm_device *dev,
                                                struct drm_framebuffer *fb,
                                                const struct drm_mode_fb_cmd2 *mode_cmd)
            {
                return;
            }" > conftest$$.c;

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#define NV_DRM_HELPER_MODE_FILL_FB_STRUCT_HAS_DEV_ARG" | append_conftest "function"
                echo "#define NV_DRM_HELPER_MODE_FILL_FB_STRUCT_HAS_CONST_MODE_CMD_ARG" | append_conftest "function"
                rm -f conftest$$.o
            else
                echo "#undef NV_DRM_HELPER_MODE_FILL_FB_STRUCT_HAS_DEV_ARG" | append_conftest "function"

                #
                # Determine if the drm_mode_fb_cmd2 pointer argument is const in
                # drm_mode_config_funcs::fb_create and drm_helper_mode_fill_fb_struct().
                #
                # The drm_mode_fb_cmd2 pointer through this call chain was made const by:
                #   2015-11-11  1eb83451ba55d7a8c82b76b1591894ff2d4a95f2
                #
                echo "$CONFTEST_PREAMBLE
                #include <drm/drm_crtc_helper.h>
                void drm_helper_mode_fill_fb_struct(struct drm_framebuffer *fb,
                                                    const struct drm_mode_fb_cmd2 *mode_cmd)
                {
                    return;
                }" > conftest$$.c;

                $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
                rm -f conftest$$.c

                if [ -f conftest$$.o ]; then
                    echo "#define NV_DRM_HELPER_MODE_FILL_FB_STRUCT_HAS_CONST_MODE_CMD_ARG" | append_conftest "function"
                    rm -f conftest$$.o
                else
                    echo "#undef NV_DRM_HELPER_MODE_FILL_FB_STRUCT_HAS_CONST_MODE_CMD_ARG" | append_conftest "function"
                fi
            fi
        ;;

        mm_context_t)
            #
            # Determine if the 'mm_context_t' data type is present
            # and if it has an 'id' member.
            #
            echo "$CONFTEST_PREAMBLE
            #include <linux/mm.h>
            int conftest_mm_context_t(void) {
                return offsetof(mm_context_t, id);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#define NV_MM_CONTEXT_T_HAS_ID" | append_conftest "types"
                rm -f conftest$$.o
                return
            else
                echo "#undef NV_MM_CONTEXT_T_HAS_ID" | append_conftest "types"
                return
            fi
        ;;
        get_user_pages)     
            #
            # Conftest for get_user_pages()
            #
            # Use long type for get_user_pages and unsigned long for nr_pages
            # 2013 Feb 22: 28a35716d317980ae9bc2ff2f84c33a3cda9e884
            #
            # Removed struct task_struct *tsk & struct mm_struct *mm from get_user_pages.
            # 2016 Feb 12: cde70140fed8429acf7a14e2e2cbd3e329036653
            #
            # Replaced get_user_pages6 with get_user_pages.
            # 2016 April 4: c12d2da56d0e07d230968ee2305aaa86b93a6832
            #
            # Replaced write and force parameters with gup_flags.
            # 2016 Oct 12: 768ae309a96103ed02eb1e111e838c87854d8b51
            #
            # linux-4.4.168 cherry-picked commit 768ae309a961 without
            # c12d2da56d0e which is covered in Conftest #3.
            #
            # Conftest #1: Check if get_user_pages accepts 6 arguments.
            # Return if true.
            # Fall through to conftest #2 on failure.

            echo "$CONFTEST_PREAMBLE
            #include <linux/mm.h>
            long get_user_pages(unsigned long start,
                                unsigned long nr_pages,
                                int write,
                                int force,
                                struct page **pages,
                                struct vm_area_struct **vmas) {
                return 0;
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c    
            if [ -f conftest$$.o ]; then
                echo "#define NV_GET_USER_PAGES_HAS_WRITE_AND_FORCE_ARGS" | append_conftest "functions"
                echo "#undef NV_GET_USER_PAGES_HAS_TASK_STRUCT" | append_conftest "functions"
                rm -f conftest$$.o
                return
            fi
            
            # Conftest #2: Check if get_user_pages has gup_flags instead of
            # write and force parameters. And that gup doesn't accept a
            # task_struct and mm_struct as its first arguments.
            # Return if available.
            # Fall through to conftest #3 on failure.

            echo "$CONFTEST_PREAMBLE
            #include <linux/mm.h>
            long get_user_pages(unsigned long start,
                                unsigned long nr_pages,
                                unsigned int gup_flags,
                                struct page **pages,
                                struct vm_area_struct **vmas) {
                return 0;
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#undef NV_GET_USER_PAGES_HAS_WRITE_AND_FORCE_ARGS" | append_conftest "functions"
                echo "#undef NV_GET_USER_PAGES_HAS_TASK_STRUCT" | append_conftest "functions"
                rm -f conftest$$.o
                return
            fi

            # Conftest #3: Check if get_user_pages has gup_flags instead of
            # write and force parameters AND that gup has task_struct and
            # mm_struct as its first arguments.
            # Return if available.
            # Fall through to default case if absent.

            echo "$CONFTEST_PREAMBLE
            #include <linux/mm.h>
            long get_user_pages(struct task_struct *tsk,
                                struct mm_struct *mm,
                                unsigned long start,
                                unsigned long nr_pages,
                                unsigned int gup_flags,
                                struct page **pages,
                                struct vm_area_struct **vmas) {
                return 0;
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#undef NV_GET_USER_PAGES_HAS_WRITE_AND_FORCE_ARGS" | append_conftest "functions"
                echo "#define NV_GET_USER_PAGES_HAS_TASK_STRUCT" | append_conftest "functions"
                rm -f conftest$$.o
                return
            fi

            echo "#define NV_GET_USER_PAGES_HAS_WRITE_AND_FORCE_ARGS" | append_conftest "functions"
            echo "#define NV_GET_USER_PAGES_HAS_TASK_STRUCT" | append_conftest "functions"

            return
        ;;

        get_user_pages_remote)
            #
            # Determine if the function get_user_pages_remote() is
            # present and has write/force/locked/tsk parameters.
            #
            # get_user_pages_remote() was added by:
            #   2016 Feb 12: 1e9877902dc7e11d2be038371c6fbf2dfcd469d7
            #
            # get_user_pages[_remote]() write/force parameters
            # replaced with gup_flags:
            #   2016 Oct 12: 768ae309a96103ed02eb1e111e838c87854d8b51
            #   2016 Oct 12: 9beae1ea89305a9667ceaab6d0bf46a045ad71e7
            #
            # get_user_pages_remote() added 'locked' parameter
            #   2016 Dec 14:5b56d49fc31dbb0487e14ead790fc81ca9fb2c99
            #
            # get_user_pages_remote() removed 'tsk' parameter by
            # commit 64019a2e467a ("mm/gup: remove task_struct pointer for
            # all gup code") in v5.9-rc1 (2020-08-11).
            #
            # conftest #1: check if get_user_pages_remote() is available
            # return if not available.
            # Fall through to conftest #2 if it is present

            echo "$CONFTEST_PREAMBLE
            #include <linux/mm.h>
            void conftest_get_user_pages_remote(void) {
                get_user_pages_remote();
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#undef NV_GET_USER_PAGES_REMOTE_PRESENT" | append_conftest "functions"
                echo "#undef NV_GET_USER_PAGES_REMOTE_HAS_TSK_ARG" | append_conftest "functions"
                echo "#undef NV_GET_USER_PAGES_REMOTE_HAS_WRITE_AND_FORCE_ARGS" | append_conftest "functions"
                echo "#undef NV_GET_USER_PAGES_REMOTE_HAS_LOCKED_ARG" | append_conftest "functions"
                rm -f conftest$$.o
                return
            fi

            # conftest #2: check if get_user_pages_remote() has write and
            # force arguments. Return if these arguments are present
            # Fall through to conftest #3 if these args are absent.
            echo "#define NV_GET_USER_PAGES_REMOTE_PRESENT" | append_conftest "functions"
            echo "$CONFTEST_PREAMBLE
            #include <linux/mm.h>
            long get_user_pages_remote(struct task_struct *tsk,
                                       struct mm_struct *mm,
                                       unsigned long start,
                                       unsigned long nr_pages,
                                       int write,
                                       int force,
                                       struct page **pages,
                                       struct vm_area_struct **vmas) {
                return 0;
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#define NV_GET_USER_PAGES_REMOTE_HAS_TSK_ARG" | append_conftest "functions"
                echo "#define NV_GET_USER_PAGES_REMOTE_HAS_WRITE_AND_FORCE_ARGS" | append_conftest "functions"
                echo "#undef NV_GET_USER_PAGES_REMOTE_HAS_LOCKED_ARG" | append_conftest "functions"
                rm -f conftest$$.o
                return
            fi

            echo "#undef NV_GET_USER_PAGES_REMOTE_HAS_WRITE_AND_FORCE_ARGS" | append_conftest "functions"

            #
            # conftest #3: check if get_user_pages_remote() has locked argument
            # Return if these arguments are present. Fall through to conftest #4
            # if these args are absent.
            #
            echo "$CONFTEST_PREAMBLE
            #include <linux/mm.h>
            long get_user_pages_remote(struct task_struct *tsk,
                                       struct mm_struct *mm,
                                       unsigned long start,
                                       unsigned long nr_pages,
                                       unsigned int gup_flags,
                                       struct page **pages,
                                       struct vm_area_struct **vmas,
                                       int *locked) {
                return 0;
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#define NV_GET_USER_PAGES_REMOTE_HAS_TSK_ARG" | append_conftest "functions"
                echo "#define NV_GET_USER_PAGES_REMOTE_HAS_LOCKED_ARG" | append_conftest "functions"
                rm -f conftest$$.o
                return
            fi

            #
            # conftest #4: check if get_user_pages_remote() does not take
            # tsk argument.
            #
            echo "$CONFTEST_PREAMBLE
            #include <linux/mm.h>
            long get_user_pages_remote(struct mm_struct *mm,
                                       unsigned long start,
                                       unsigned long nr_pages,
                                       unsigned int gup_flags,
                                       struct page **pages,
                                       struct vm_area_struct **vmas,
                                       int *locked) {
                return 0;
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#undef NV_GET_USER_PAGES_REMOTE_HAS_TSK_ARG" | append_conftest "functions"
                echo "#define NV_GET_USER_PAGES_REMOTE_HAS_LOCKED_ARG" | append_conftest "functions"
                rm -f conftest$$.o
            else

                echo "#define NV_GET_USER_PAGES_REMOTE_HAS_TSK_ARG" | append_conftest "functions"
                echo "#undef NV_GET_USER_PAGES_REMOTE_HAS_LOCKED_ARG" | append_conftest "functions"
            fi
        ;;

        usleep_range)
            #
            # Determine if the function usleep_range() is present.
            #
            # usleep_range() was added by:
            #  2010 Aug 4 : 5e7f5a178bba45c5aca3448fddecabd4e28f1f6b
            #
            CODE="
            #include <linux/delay.h>
            void conftest_usleep_range(void) {
                usleep_range();
            }"

            compile_check_conftest "$CODE" "NV_USLEEP_RANGE_PRESENT" "" "functions"
        ;;

         radix_tree_empty)
            #
            # Determine if the function  radix_tree_empty() is present.
            #
            #  radix_tree_empty() was added by:
            #  2016 May 21 : e9256efcc8e390fa4fcf796a0c0b47d642d77d32
            #
            CODE="
            #include <linux/radix-tree.h>
            int conftest_radix_tree_empty(void) {
                radix_tree_empty();
            }"

            compile_check_conftest "$CODE" "NV_RADIX_TREE_EMPTY_PRESENT" "" "functions"
        ;;

        drm_gem_object_lookup)
            #
            # Determine the number of arguments of drm_gem_object_lookup().
            #
            # drm_gem_object_lookup() was originally added to the kernel by:
            #  2008-07-30 : 673a394b1e3b69be886ff24abfd6df97c52e8d08
            #
            # First argument of type drm_device has been removed by:
            #  2016-05-09 : a8ad0bd84f986072314595d05444719fdf29e412
            #
            echo "$CONFTEST_PREAMBLE
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif
            #if defined(NV_DRM_DRM_GEM_H_PRESENT)
            #include <drm/drm_gem.h>
            #endif
            void conftest_drm_gem_object_lookup(void) {
                drm_gem_object_lookup(NULL, NULL, 0);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#define NV_DRM_GEM_OBJECT_LOOKUP_PRESENT" | append_conftest "functions"
                echo "#define NV_DRM_GEM_OBJECT_LOOKUP_ARGUMENT_COUNT 3" | append_conftest "functions"
                rm -f conftest$$.o
                return
            fi

            echo "$CONFTEST_PREAMBLE
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif
            #if defined(NV_DRM_DRM_GEM_H_PRESENT)
            #include <drm/drm_gem.h>
            #endif
            void conftest_drm_gem_object_lookup(void) {
                drm_gem_object_lookup(NULL, 0);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#define NV_DRM_GEM_OBJECT_LOOKUP_PRESENT" | append_conftest "functions"
                echo "#define NV_DRM_GEM_OBJECT_LOOKUP_ARGUMENT_COUNT 2" | append_conftest "functions"
                rm -f conftest$$.o
            else
                echo "#undef NV_DRM_GEM_OBJECT_LOOKUP_PRESENT" | append_conftest "functions"
                echo "#undef NV_DRM_GEM_OBJECT_LOOKUP_ARGUMENT_COUNT" | append_conftest "functions"
            fi
        ;;

        drm_master_drop_has_from_release_arg)
            #
            # Determine if drm_driver::master_drop() has 'from_release' argument.
            #
            # Last argument 'bool from_release' has been removed by:
            #  2016-06-21 : d6ed682eba54915ea56315bc2e5a33fca5922997
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            void conftest_drm_master_drop_has_from_release_arg(struct drm_driver *drv) {
                drv->master_drop(NULL, NULL, false);
            }"

            compile_check_conftest "$CODE" "NV_DRM_MASTER_DROP_HAS_FROM_RELEASE_ARG" "" "types"
        ;;

        drm_mode_config_funcs_has_atomic_state_alloc)
            #
            # Determine if the 'drm_mode_config_funcs' structure has
            # an 'atomic_state_alloc' field.
            #
            # added:   2015-05-18  036ef5733ba433760a3512bb5f7a155946e2df05
            #
            CODE="
            #include <drm/drm_crtc.h>
            int conftest_drm_mode_config_funcs_has_atomic_state_alloc(void) {
                return offsetof(struct drm_mode_config_funcs, atomic_state_alloc);
            }"

            compile_check_conftest "$CODE" "NV_DRM_MODE_CONFIG_FUNCS_HAS_ATOMIC_STATE_ALLOC" "" "types"
        ;;

        drm_atomic_modeset_nonblocking_commit_available)
            #
            # Determine if nonblocking commit support avaiable in the DRM atomic
            # modesetting subsystem.
            #
            # added:   2016-05-08  9f2a7950e77abf00a2a87f3b4cbefa36e9b6009b
            #
            CODE="
            #include <drm/drm_crtc.h>
            int conftest_drm_atomic_modeset_nonblocking_commit_available(void) {
                return offsetof(struct drm_mode_config, helper_private);
            }"

            compile_check_conftest "$CODE" "NV_DRM_ATOMIC_MODESET_NONBLOCKING_COMMIT_AVAILABLE" "" "generic"
        ;;

        drm_atomic_state_ref_counting)
            #
            # Determine if functions drm_atomic_state_get/put() are
            # present.
            #
            # Added by commit 0853695c3ba4 ("drm: Add reference counting to
            # drm_atomic_state") in v4.10 (2016-10-14)
            #
            CODE="
            #if defined(NV_DRM_DRM_ATOMIC_H_PRESENT)
            #include <drm/drm_atomic.h>
            #endif
            void conftest_drm_atomic_state_get(void) {
                drm_atomic_state_get();
            }"

            compile_check_conftest "$CODE" "NV_DRM_ATOMIC_STATE_REF_COUNTING_PRESENT" "" "functions"
        ;;

        vm_ops_fault_removed_vma_arg)
            #
            # Determine if vma.vm_ops.fault takes (vma, vmf), or just (vmf)
            # args. Acronym key:
            #   vma: struct vm_area_struct
            #   vm_ops: struct vm_operations_struct
            #   vmf: struct vm_fault
            #
            # The redundant vma arg was removed from BOTH vma.vm_ops.fault and
            # vma.vm_ops.page_mkwrite, with the following commit:
            #
            #   2017-02-24  11bac80004499ea59f361ef2a5516c84b6eab675
            #
            CODE="
            #include <linux/mm.h>
            void conftest_vm_ops_fault_removed_vma_arg(void) {
                struct vm_operations_struct vm_ops;
                struct vm_fault *vmf;
                (void)vm_ops.fault(vmf);
            }"

            compile_check_conftest "$CODE" "NV_VM_OPS_FAULT_REMOVED_VMA_ARG" "" "types"
        ;;

        pnv_npu2_init_context)
            #
            # Determine if the pnv_npu2_init_context() function is
            # present.
            #
            CODE="
            #if defined(NV_ASM_POWERNV_H_PRESENT)
            #include <linux/pci.h>
            #include <asm/powernv.h>
            #endif
            void conftest_pnv_npu2_init_context(void) {
                pnv_npu2_init_context();
            }"

            compile_check_conftest "$CODE" "NV_PNV_NPU2_INIT_CONTEXT_PRESENT" "" "functions"
        ;;

        drm_driver_unload_has_int_return_type)
            #
            # Determine if drm_driver::unload() returns integer value, which has
            # been changed to void by commit -
            #
            #   2017-01-06  11b3c20bdd15d17382068be569740de1dccb173d
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            int conftest_drm_driver_unload_has_int_return_type(struct drm_driver *drv) {
                return drv->unload(NULL /* dev */);
            }"

            compile_check_conftest "$CODE" "NV_DRM_DRIVER_UNLOAD_HAS_INT_RETURN_TYPE" "" "types"
        ;;

        kref_has_refcount_of_type_refcount_t)
            CODE="
            #include <linux/kref.h>

            refcount_t conftest_kref_has_refcount_of_type_refcount_t(struct kref *ref) {
                return ref->refcount;
            }"

            compile_check_conftest "$CODE" "NV_KREF_HAS_REFCOUNT_OF_TYPE_REFCOUNT_T" "" "types"
        ;;

        is_export_symbol_present_*)
            export_symbol_present_conftest $(echo $1 | cut -f5- -d_)
        ;;

        is_export_symbol_gpl_*)
            export_symbol_gpl_conftest $(echo $1 | cut -f5- -d_)
        ;;

        drm_atomic_helper_disable_all)
            #
            # Determine if the function drm_atomic_helper_disable_all() is
            # present.
            #
            # drm_atomic_helper_disable_all() has been added by:
            #   2015-12-02  1494276000db789c6d2acd85747be4707051c801
            #
            CODE="
            #if defined(NV_DRM_DRM_ATOMIC_HELPER_H_PRESENT)
            #include <drm/drm_atomic_helper.h>
            #endif
            void conftest_drm_atomic_helper_disable_all(void) {
                drm_atomic_helper_disable_all();
            }"

            compile_check_conftest "$CODE" "NV_DRM_ATOMIC_HELPER_DISABLE_ALL_PRESENT" "" "functions"
        ;;

        drm_atomic_helper_set_config)
            #
            # Determine if drm_atomic_helper_set_config() has 'ctx' argument.
            #
            # drm_atomic_helper_set_config() was added by:
            #   2014-06-27  042652ed95996a9ef6dcddddc53b5d8bc7fa887e
            # and it has been updated to take ctx parameter by:
            #   2017-03-22  a4eff9aa6db8eb3d1864118f3558214b26f630b4
            #
            echo "$CONFTEST_PREAMBLE
            #if defined(NV_DRM_DRM_ATOMIC_HELPER_H_PRESENT)
            #include <drm/drm_atomic_helper.h>
            #endif
            void conftest_drm_atomic_helper_set_config(void) {
                drm_atomic_helper_set_config();
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#undef NV_DRM_ATOMIC_HELPER_SET_CONFIG_PRESENT" | append_conftest "functions"
            else
                echo "#define NV_DRM_ATOMIC_HELPER_SET_CONFIG_PRESENT" | append_conftest "functions"

                echo "$CONFTEST_PREAMBLE
                #include <drm/drm_atomic_helper.h>
                int drm_atomic_helper_set_config(struct drm_mode_set *set,
                                                 struct drm_modeset_acquire_ctx *ctx) {
                    return 0;
                }" > conftest$$.c

                $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
                rm -f conftest$$.c

                if [ -f conftest$$.o ]; then
                    echo "#define NV_DRM_ATOMIC_HELPER_SET_CONFIG_HAS_CTX_ARG" | append_conftest "types"
                    rm -f conftest$$.o
                else
                    echo "#undef NV_DRM_ATOMIC_HELPER_SET_CONFIG_HAS_CTX_ARG" | append_conftest "types"
                fi
            fi
        ;;

        drm_atomic_helper_crtc_destroy_state_has_crtc_arg)
            #
            # Determine if __drm_atomic_helper_crtc_destroy_state() has 'crtc'
            # argument.
            #
            # __drm_atomic_helper_crtc_destroy_state() is updated to drop
            # crtc argument by:
            #   2016-05-09  ec2dc6a0fe38de8d73a7b7638a16e7d33a19a5eb
            #
            CODE="
            #if defined(NV_DRM_DRM_ATOMIC_HELPER_H_PRESENT)
            #include <drm/drm_atomic_helper.h>
            #endif
            void conftest_drm_atomic_helper_crtc_destroy_state_has_crtc_arg(void) {
                __drm_atomic_helper_crtc_destroy_state(NULL, NULL);
            }"

            compile_check_conftest "$CODE" "NV_DRM_ATOMIC_HELPER_CRTC_DESTROY_STATE_HAS_CRTC_ARG" "" "types"
        ;;

        drm_atomic_helper_connector_dpms)
            #
            # Determine if the function drm_atomic_helper_connector_dpms() is present.
            #
            # drm_atomic_helper_connector_dpms() was removed by:
            #   2017-07-25 7d902c05b480cc44033dcb56e12e51b082656b42
            #
            CODE="
            #if defined(NV_DRM_DRM_ATOMIC_HELPER_H_PRESENT)
            #include <drm/drm_atomic_helper.h>
            #endif
            void conftest_drm_atomic_helper_connector_dpms(void) {
                drm_atomic_helper_connector_dpms();
            }"

            compile_check_conftest "$CODE" "NV_DRM_ATOMIC_HELPER_CONNECTOR_DPMS_PRESENT" "" "functions"
        ;;

        backlight_device_register)
            #
            # Determine if the backlight_device_register() function is present
            # and how many arguments it takes.
            #
            # Don't try to support the 4-argument form of backlight_device_register().
            #
            echo "$CONFTEST_PREAMBLE
            #include <linux/backlight.h>
            #if !defined(CONFIG_BACKLIGHT_CLASS_DEVICE)
            #error Backlight class device not enabled
            #endif
            void conftest_backlight_device_register(void) {
                backlight_device_register(NULL, NULL, NULL, NULL, NULL);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#define NV_BACKLIGHT_DEVICE_REGISTER_PRESENT" | append_conftest "functions"
                return
            else
                echo "#undef NV_BACKLIGHT_DEVICE_REGISTER_PRESENT" | append_conftest "functions"
                return
            fi
        ;;

        backlight_properties_type)
            #
            # Determine if the backlight_properties structure has a 'type' field
            # and whether BACKLIGHT_RAW is defined.
            #
            CODE="
            #include <linux/backlight.h>
            void conftest_backlight_props_type(void) {
                struct backlight_properties tmp;
                tmp.type = BACKLIGHT_RAW;
            }"

            compile_check_conftest "$CODE" "NV_BACKLIGHT_PROPERTIES_TYPE_PRESENT" "" "types"
        ;;

        register_acpi_notifier)
            #
            # Determine if the register_acpi_notifier() and unregister_acpi_notifier()
            # functions are present.
            #
            # register_acpi_notifier() and unregister_acpi_notifier() are
            # added by:
            #     2008-01-25  9ee85241fdaab358dff1d8647f20a478cfa512a1
            #
            CODE="
            #include <acpi/acpi_bus.h>
            int conftest_register_acpi_notifier(void) {
                return register_acpi_notifier();
            }"
            compile_check_conftest "$CODE" "NV_REGISTER_ACPI_NOTIFER_PRESENT" "" "functions"
        ;;

        timer_setup)
            #
            # Determine if the function timer_setup() is present.
            #
            # timer_setup() was added by:
            #     2017-09-28  686fef928bba6be13cabe639f154af7d72b63120
            #
            CODE="
            #include <linux/timer.h>
            int conftest_timer_setup(void) {
                return timer_setup();
            }"
            compile_check_conftest "$CODE" "NV_TIMER_SETUP_PRESENT" "" "functions"
        ;;

        radix_tree_replace_slot)
            #
            # Determine if the radix_tree_replace_slot() function is
            # present and how many arguments it takes.
            #
            # radix_tree_replace_slot added
            #   2006-12-06 7cf9c2c76c1a17b32f2da85b50cd4fe468ed44b5
            # root parameter added to radix_tree_replace_slot in 4.10 (but the symbol was not exported)
            #   2016-12-12 6d75f366b9242f9b17ed7d0b0604d7460f818f21
            # radix_tree_replace_slot symbol export was introduced in 4.11
            #   2017-10-11 10257d719686706aa669b348309cfd9fd9783ad9
            #
            CODE="
            #include <linux/bug.h>
            #include <linux/version.h>
            void conftest_radix_tree_replace_slot(void) {
                BUILD_BUG_ON(LINUX_VERSION_CODE < KERNEL_VERSION(4, 10, 0) || LINUX_VERSION_CODE >= KERNEL_VERSION(4, 11, 0));
            }"
            compile_check_conftest "$CODE" "NV_RADIX_TREE_REPLACE_SLOT_PRESENT" "" "functions"

            echo "$CONFTEST_PREAMBLE
            #include <linux/radix-tree.h>
            void conftest_radix_tree_replace_slot(void) {
                radix_tree_replace_slot(NULL, NULL);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#define NV_RADIX_TREE_REPLACE_SLOT_ARGUMENT_COUNT 2" | append_conftest "functions"
                return
            fi

            echo "$CONFTEST_PREAMBLE
            #include <linux/radix-tree.h>
            void conftest_radix_tree_replace_slot(void) {
                radix_tree_replace_slot(NULL, NULL, NULL);
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#define NV_RADIX_TREE_REPLACE_SLOT_ARGUMENT_COUNT 3" | append_conftest "functions"
                return
            else
                echo "#error radix_tree_replace_slot() conftest failed!" | append_conftest "functions"
            fi
        ;;

        drm_old_atomic_state_iterators_present)
            #
            # Determine if the old atomic state iterators
            # for_each_crtc_in_state(), for_each_connector_in_state() and
            # for_each_plane_in_state() are present.
            #
            # These old atomic state iterators were added by:
            #   2015-04-10  df63b9994eaf942afcdb946d27a28661d7dfbf2a
            # and they are removed by:
            #   2017-07-19  77ac3b00b13185741effd0d5e2f1f05e4bfef7dc
            #
            CODE="
            #include <drm/drmP.h>
            #include <drm/drm_atomic.h>
            void conftest_drm_old_atomic_state_iterators_present(void) {
                struct drm_crtc_state *crtc_state;
                struct drm_atomic_state *state;
                struct drm_crtc *crtc;
                int i;

                for_each_crtc_in_state(state, crtc, crtc_state, i) {
                }
            }"

            compile_check_conftest "$CODE" "NV_DRM_OLD_ATOMIC_STATE_ITERATORS_PRESENT" | append_conftest "types"
        ;;

        drm_mode_object_find_has_file_priv_arg)
            #
            # Determine if drm_mode_object_find() has 'file_priv' arguments.
            #
            # The function drm_mode_object_find() was added by:
            #   2008-11-07  f453ba0460742ad027ae0c4c7d61e62817b3e7ef
            # and it is updated to take 'file_priv' argument by:
            #   2017-03-14  418da17214aca5ef5f0b6f7588905ee7df92f98f
            #
            CODE="
            #include <drm/drm_mode_object.h>
            void conftest_drm_mode_object_find_has_file_priv_arg(
                    struct drm_device *dev,
                    struct drm_file *file_priv,
                    uint32_t id,
                    uint32_t type) {
                (void)drm_mode_object_find(dev, file_priv, id, type);
            }"

            compile_check_conftest "$CODE" "NV_DRM_MODE_OBJECT_FIND_HAS_FILE_PRIV_ARG" | append_conftest "types"
        ;;
        kmem_cache_create_usercopy)
            #
            # Determine if the kmem_cache_create_usercopy function exists.
            #
            # This function was added by:
            #   2017-06-10  8eb8284b412906181357c2b0110d879d5af95e52
            CODE="
            #include <linux/slab.h>
            void kmem_cache_create_usercopy(void) {
                kmem_cache_create_usercopy();
            }"

            compile_check_conftest "$CODE" "NV_KMEM_CACHE_CREATE_USERCOPY_PRESENT" "" "functions"
        ;;

        drm_connector_funcs_have_mode_in_name)
            #
            # Determine if _mode_ is present in connector function names.
            #
            # _mode_ has been dropped from connector function names by commits:
            #   2018-07-09  c555f02371c338b06752577aebf738dbdb6907bd
            #   2018-07-09  cde4c44d8769c1be16074c097592c46c7d64092b
            #   2018-07-09  97e14fbeb53fe060c5f6a7a07e37fd24c087ed0c
            #
            CODE="
            #include <drm/drm_connector.h>
            void conftest_drm_connector_funcs_have_mode_in_name(void) {
                drm_mode_connector_attach_encoder();
            }"

            compile_check_conftest "$CODE" "NV_DRM_CONNECTOR_FUNCS_HAVE_MODE_IN_NAME" "" "functions"
        ;;

        vm_fault_t)
            #
            # Determine if vm_fault_t is present
            #
            # Added by commit 1c8f422059ae5da07db7406ab916203f9417e396 ("mm:
            # change return type to vm_fault_t") in v4.17 (2018-04-05)
            #
            CODE="
            #include <linux/mm.h>
            vm_fault_t conftest_vm_fault_t;
            "
            compile_check_conftest "$CODE" "NV_VM_FAULT_T_IS_PRESENT" "" "types"
        ;;

        vmf_insert_pfn)
            #
            # Determine if the function vmf_insert_pfn() is
            # present.
            #
            # Added by commit 1c8f422059ae5da07db7406ab916203f9417e396 ("mm:
            # change return type to vm_fault_t") in v4.17 (2018-04-05)
            #
            CODE="
            #include <linux/mm.h>
            void conftest_vmf_insert_pfn(void) {
                vmf_insert_pfn();
            }"

            compile_check_conftest "$CODE" "NV_VMF_INSERT_PFN_PRESENT" "" "functions"
        ;;

        do_gettimeofday)
            #
            # Determine if the function do_gettimeofday() is
            # present.
            #
            # Added by commit 7a2deb32924142696b8174cdf9b38cd72a11fc96
            # (2002-02-04) in v2.5.0, moved from linux/time.h to
            # linux/timekeeping.h by commit
            # 8b094cd03b4a3793220d8d8d86a173bfea8c285b (2014-07-16) in v3.17,
            # and removed by e4b92b108c6cd6b311e4b6e85d6a87a34599a6e3
            # (2018-12-07).
            #
            # Header file linux/ktime.h added by commit
            # 97fc79f97b1111c80010d34ee66312b88f531e41 (2006-06-09) in v2.6.16,
            # includes linux/time.h and/or linux/timekeeping.h.
            #
            CODE="
            #include <linux/time.h>
            #if defined(NV_LINUX_KTIME_H_PRESENT)
            #include <linux/ktime.h>
            #endif
            void conftest_do_gettimeofday(void) {
                do_gettimeofday();
            }"

            compile_check_conftest "$CODE" "NV_DO_GETTIMEOFDAY_PRESENT" "" "functions"
        ;;

        drm_framebuffer_get)
            #
            # Determine if the function drm_framebuffer_get() is present.
            #
            # Added by commit a4a69da06bc11a937a6e417938b1bb698ee1fa46 (drm:
            # Introduce drm_framebuffer_{get,put}()) on 2017-02-28.
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            #if defined(NV_DRM_DRM_FRAMEBUFFER_H_PRESENT)
            #include <drm/drm_framebuffer.h>
            #endif

            void conftest_drm_framebuffer_get(void) {
                drm_framebuffer_get();
            }"

            compile_check_conftest "$CODE" "NV_DRM_FRAMEBUFFER_GET_PRESENT" "" "functions"
        ;;

        drm_gem_object_get)
            #
            # Determine if the function drm_gem_object_get() is present.
            #
            # Added by commit e6b62714e87c8811d5564b6a0738dcde63a51774 (drm:
            # Introduce drm_gem_object_{get,put}()) on 2017-02-28.
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            #if defined(NV_DRM_DRM_GEM_H_PRESENT)
            #include <drm/drm_gem.h>
            #endif
            void conftest_drm_gem_object_get(void) {
                drm_gem_object_get();
            }"

            compile_check_conftest "$CODE" "NV_DRM_GEM_OBJECT_GET_PRESENT" "" "functions"
        ;;

        drm_dev_put)
            #
            # Determine if the function drm_dev_put() is present.
            #
            # Added by commit 9a96f55034e41b4e002b767e9218d55f03bdff7d (drm:
            # introduce drm_dev_{get/put} functions) on 2017-09-26.
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            #if defined(NV_DRM_DRM_DRV_H_PRESENT)
            #include <drm/drm_drv.h>
            #endif
            void conftest_drm_dev_put(void) {
                drm_dev_put();
            }"

            compile_check_conftest "$CODE" "NV_DRM_DEV_PUT_PRESENT" "" "functions"
        ;;

        drm_connector_list_iter)
            #
            # Determine if the drm_connector_list_iter struct is present.
            #
            # Added by commit 613051dac40da1751ab269572766d3348d45a197 ("drm:
            # locking&new iterators for connector_list") in v4.11 (2016-12-14).
            #
            CODE="
            #include <drm/drm_connector.h>
            int conftest_drm_connector_list_iter(void) {
                struct drm_connector_list_iter conn_iter;
            }"

            compile_check_conftest "$CODE" "NV_DRM_CONNECTOR_LIST_ITER_PRESENT" "" "types"

            #
            # Determine if the function drm_connector_list_iter_get() is
            # renamed to drm_connector_list_iter_begin().
            #
            # Renamed by b982dab1e66d2b998e80a97acb6eaf56518988d3 (drm: Rename
            # connector list iterator API) in v4.12 (2017-02-28).
            #
            CODE="
            #if defined(NV_DRM_DRM_CONNECTOR_H_PRESENT)
            #include <drm/drm_connector.h>
            #endif
            void conftest_drm_connector_list_iter_begin(void) {
                drm_connector_list_iter_begin();
            }"

            compile_check_conftest "$CODE" "NV_DRM_CONNECTOR_LIST_ITER_BEGIN_PRESENT" "" "functions"
        ;;

        drm_atomic_helper_swap_state_has_stall_arg)
            #
            # Determine if drm_atomic_helper_swap_state() has 'stall' argument.
            #
            # drm_atomic_helper_swap_state() function prototype updated to take
            # 'state' and 'stall' arguments by commit
            # 5e84c2690b805caeff3b4c6c9564c7b8de54742d (drm/atomic-helper:
            # Massage swap_state signature somewhat)
            # in v4.8 (2016-06-10).
            #
            CODE="
            #include <drm/drm_atomic_helper.h>
            void conftest_drm_atomic_helper_swap_state_has_stall_arg(
                    struct drm_atomic_state *state,
                    bool stall) {
                (void)drm_atomic_helper_swap_state(state, stall);
            }"

            compile_check_conftest "$CODE" "NV_DRM_ATOMIC_HELPER_SWAP_STATE_HAS_STALL_ARG" | append_conftest "types"

            #
            # Determine if drm_atomic_helper_swap_state() returns int.
            #
            # drm_atomic_helper_swap_state() function prototype
            # updated to return int by commit
            # c066d2310ae9bbc695c06e9237f6ea741ec35e43 (drm/atomic: Change
            # drm_atomic_helper_swap_state to return an error.) in v4.14
            # (2017-07-11).
            #
            CODE="
            #include <drm/drm_atomic_helper.h>
            int conftest_drm_atomic_helper_swap_state_return_int(
                    struct drm_atomic_state *state,
                    bool stall) {
                return drm_atomic_helper_swap_state(state, stall);
            }"

            compile_check_conftest "$CODE" "NV_DRM_ATOMIC_HELPER_SWAP_STATE_RETURN_INT" | append_conftest "types"
        ;;

        dma_direct_map_resource)
            #
            # Determine whether dma_is_direct() exists.
            #
            # dma_is_direct() was added by commit 356da6d0cde3 ("dma-mapping:
            # bypass indirect calls for dma-direct") in  (2018-12-06).
            #
            # If dma_is_direct() does exist, then we assume that
            # dma_direct_map_resource() exists.  Both functions were added
            # as part of the same patchset.
            #
            # The presence of dma_is_direct() and dma_direct_map_resource()
            # means that dma_direct can perform DMA mappings itself.
            #
            CODE="
            #include <linux/dma-mapping.h>
            void conftest_dma_is_direct(void) {
                dma_is_direct();
            }"

            compile_check_conftest "$CODE" "NV_DMA_IS_DIRECT_PRESENT" "" "functions"
        ;;

        drm_driver_prime_flag_present)
            #
            # Determine whether driver feature flag DRIVER_PRIME is present.
            #
            # The DRIVER_PRIME flag was added by commit 3248877ea179 (drm:
            # base prime/dma-buf support (v5)) in v3.4 (2011-11-25) and is
            # removed by commit 0424fdaf883a (drm/prime: Actually remove
            # DRIVER_PRIME everywhere) on 2019-06-17.
            #
            # DRIVER_PRIME definition moved from drmP.h to drm_drv.h by
            # commit 85e634bce01a (drm: Extract drm_drv.h) in v4.10
            # (2016-11-14).
            #
            # DRIVER_PRIME define is changed to enum value by commit
            # 0e2a933b02c9 (drm: Switch DRIVER_ flags to an enum) in v5.1
            # (2019-01-29).
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            #if defined(NV_DRM_DRM_DRV_H_PRESENT)
            #include <drm/drm_drv.h>
            #endif

            unsigned int drm_driver_prime_flag_present_conftest(void) {
                return DRIVER_PRIME;
            }"

            compile_check_conftest "$CODE" "NV_DRM_DRIVER_PRIME_FLAG_PRESENT" "" "types"
        ;;

        drm_gem_prime_export_has_dev_arg)
            #
            # Determine if drm_driver::gem_prime_export() has 'dev' argument.
            #
            # The 'dev' argument has been dropped from
            # drm_driver::gem_prime_export() by commit e4fa8457b219 (drm/prime:
            # Align gem_prime_export with obj_funcs.export) in v5.4-rc1
            # (2019-06-14).
            #
            CODE="
            #include <drm/drmP.h>
            #if defined(NV_DRM_DRM_DRV_H_PRESENT)
            #include <drm/drm_drv.h>
            #endif
            struct dma_buf *conftest_drm_gem_prime_export_has_dev_arg(
                struct drm_driver *drv,
                struct drm_device *dev, struct drm_gem_object *obj, int flags) {
                return drv->gem_prime_export(dev, obj, flags);
            }"

            compile_check_conftest "$CODE" "NV_DRM_GEM_PRIME_EXPORT_HAS_DEV_ARG" "" "types"
        ;;

        drm_connector_for_each_possible_encoder)
            #
            # Determine the number of arguments of the
            # drm_connector_for_each_possible_encoder() macro.
            #
            # drm_connector_for_each_possible_encoder() is added by commit
            # 83aefbb887b5 (drm: Add drm_connector_for_each_possible_encoder())
            # in v4.19. The definition and prorotype is changed to take only
            # two arguments connector and encoder, by commit 62afb4ad425a
            # (drm/connector: Allow max possible encoders to attach to a
            # connector) in v5.5rc1.
            #
            echo "$CONFTEST_PREAMBLE
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            #if defined(NV_DRM_CONNECTOR_H_PRESENT)
            #include <drm/drm_connector.h>
            #endif

            void conftest_drm_connector_for_each_possible_encoder(
                struct drm_connector *connector,
                struct drm_encoder *encoder,
                int i) {

                drm_connector_for_each_possible_encoder(connector, encoder, i) {
                }
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                echo "#define NV_DRM_CONNECTOR_FOR_EACH_POSSIBLE_ENCODER_ARGUMENT_COUNT 3" | append_conftest "functions"
                rm -f conftest$$.o
                return
            else
                echo "#define NV_DRM_CONNECTOR_FOR_EACH_POSSIBLE_ENCODER_ARGUMENT_COUNT 2" | append_conftest "functions"
            fi
        ;;

        drm_gem_object_has_resv)
            #
            # Determine if the 'drm_gem_object' structure has a 'resv' field.
            #
            # A 'resv' filed in the 'drm_gem_object' structure, is added by
            # commit 1ba627148ef5 (drm: Add reservation_object to
            # drm_gem_object) in v5.2.
            #
            CODE="$CONFTEST_PREAMBLE
            #if defined(NV_DRM_DRM_GEM_H_PRESENT)
            #include <drm/drm_gem.h>
            #endif

            int conftest_drm_gem_object_has_resv(void) {
                return offsetof(struct drm_gem_object, resv);
            }"

            compile_check_conftest "$CODE" "NV_DRM_GEM_OBJECT_HAS_RESV" "" "types"
        ;;

        proc_ops)
            #
            # Determine if the 'struct proc_ops' type is present.
            #
            # Added by commit d56c0d45f0e2 ("proc: decouple proc from VFS with 
            # "struct proc_ops"") in 5.6-rc1
            #
            CODE="
            #include <linux/proc_fs.h>

            struct proc_ops p_ops;
            "

            compile_check_conftest "$CODE" "NV_PROC_OPS_PRESENT" "" "types"
        ;;

        timeval)
            #
            # Determine if the 'struct timeval' type is present.
            #
            # Removed by commit c766d1472c70 ("y2038: hide 
            # timeval/timespec/itimerval/itimerspec types") in 5.6-rc3
            # (2020-02-20).
            #
            CODE="
            #include <linux/time.h>

            struct timeval tm;
            "

            compile_check_conftest "$CODE" "NV_TIMEVAL_PRESENT" "" "types"
        ;;

        ktime_get_raw_ts64)
            #
            # Determine if ktime_get_raw_ts64() is present
            #
            # Added by commit fb7fcc96a86cf ("timekeeping: Standardize on
            # ktime_get_*() naming") in 4.18 (2018-04-27)
            #
        CODE="
        #include <linux/ktime.h>
        void conftest_ktime_get_raw_ts64(void){
            ktime_get_raw_ts64();
        }"
            compile_check_conftest "$CODE" "NV_KTIME_GET_RAW_TS64_PRESENT" "" "functions"
        ;;

        ktime_get_real_ts64)
            #
            # Determine if ktime_get_real_ts64() is present
            #
            # Added by commit d6d29896c665d ("timekeeping: Provide timespec64
            # based interfaces") in 3.17 (2014-07-16)
            #
        CODE="
        #include <linux/ktime.h>
        void conftest_ktime_get_real_ts64(void){
            ktime_get_real_ts64();
        }"
            compile_check_conftest "$CODE" "NV_KTIME_GET_REAL_TS64_PRESENT" "" "functions"
        ;;

        mm_has_mmap_lock)
            #
            # Determine if the 'mm_struct' structure has a 'mmap_lock' field.
            #
            # Kernel commit da1c55f1b272 ("mmap locking API: rename mmap_sem
            # to mmap_lock") replaced the field 'mmap_sem' by 'mmap_lock'
            # in v5.8-rc1 (2020-06-08).
            CODE="
            #include <linux/mm_types.h>

            int conftest_mm_has_mmap_lock(void) {
                return offsetof(struct mm_struct, mmap_lock);
            }"

            compile_check_conftest "$CODE" "NV_MM_HAS_MMAP_LOCK" "" "types"

        ;;

        pci_dev_has_skip_bus_pm)
            #
            # Determine if skip_bus_pm flag is present in struct pci_dev.
            # Presence of this flag is used to determine whether a call to
            # pci_{save/restore}_state()can be skipped and kernel PCI
            # subsystem framework will take care of saving/restoring device
            # state.
            #
            # Added by commit d491f2b75237 ("PCI: PM: Avoid possible
            # suspend-to-idle issue") in 5.2-rc3 (2019-06-13)
            #
            CODE="
            #include <linux/pci.h>
            void conftest_pci_dev_has_skip_bus_pm(void) {
                struct pci_dev dev;
                (void)dev.skip_bus_pm;
            }"

            compile_check_conftest "$CODE" "NV_PCI_DEV_HAS_SKIP_BUS_PM" "" "types"
        ;;

        vmalloc_has_pgprot_t_arg)
            #
            # Determine if __vmalloc has the 'pgprot' argument.
            #
            # The third argument to __vmalloc, page protection
            # 'pgprot_t prot', was removed by commit 88dca4ca5a93
            # (mm: remove the pgprot argument to __vmalloc)
            # in v5.8-rc1 (2020-06-01).
        CODE="
        #include <linux/vmalloc.h>

        void conftest_vmalloc_has_pgprot_t_arg(void) {
            pgprot_t prot;
            (void)__vmalloc(0, 0, prot);
        }"

            compile_check_conftest "$CODE" "NV_VMALLOC_HAS_PGPROT_T_ARG" "" "types"

        ;;

        drm_gem_object_put_unlocked)
            #
            # Determine if the function drm_gem_object_put_unlocked() is present.
            #
            # In v5.9-rc1, commit 2f4dd13d4bb8 ("drm/gem: add
            # drm_gem_object_put helper") removes drm_gem_object_put_unlocked()
            # function and replace its definition by transient macro. Commit
            # ab15d56e27be ("drm: remove transient
            # drm_gem_object_put_unlocked()") finally removes
            # drm_gem_object_put_unlocked() macro.
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            #if defined(NV_DRM_DRM_GEM_H_PRESENT)
            #include <drm/drm_gem.h>
            #endif
            void conftest_drm_gem_object_put_unlocked(void) {
                drm_gem_object_put_unlocked();
            }"

            compile_check_conftest "$CODE" "NV_DRM_GEM_OBJECT_PUT_UNLOCK_PRESENT" "" "functions"
        ;;

        drm_display_mode_has_vrefresh)
            #
            # Determine if the 'drm_display_mode' structure has a 'vrefresh'
            # field.
            #
            # Removed by commit 0425662fdf05 ("drm: Nuke mode->vrefresh") in
            # v5.9-rc1.
            #
            CODE="
            #include <drm/drm_modes.h>

            int conftest_drm_display_mode_has_vrefresh(void) {
                return offsetof(struct drm_display_mode, vrefresh);
            }"

            compile_check_conftest "$CODE" "NV_DRM_DISPLAY_MODE_HAS_VREFRESH" "types"

        ;;

        drm_driver_master_set_has_int_return_type)
            #
            # Determine if drm_driver::master_set() returns integer value
            #
            # Changed to void by commit 907f53200f98 ("drm: vmwgfx: remove
            # drm_driver::master_set() return type") in v5.9-rc1.
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            #if defined(NV_DRM_DRM_DRV_H_PRESENT)
            #include <drm/drm_drv.h>
            #endif

            int conftest_drm_driver_master_set_has_int_return_type(struct drm_driver *drv,
                struct drm_device *dev, struct drm_file *file_priv, bool from_open) {

                return drv->master_set(dev, file_priv, from_open);
            }"

            compile_check_conftest "$CODE" "NV_DRM_DRIVER_SET_MASTER_HAS_INT_RETURN_TYPE" "" "types"
        ;;

        drm_driver_has_gem_free_object)
            #
            # Determine if the 'drm_driver' structure has a 'gem_free_object'
            # function pointer.
            #
            # drm_driver::gem_free_object is removed by commit 1a9458aeb8eb
            # ("drm: remove drm_driver::gem_free_object") in v5.9-rc1.
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            #if defined(NV_DRM_DRM_DRV_H_PRESENT)
            #include <drm/drm_drv.h>
            #endif

            int conftest_drm_driver_has_gem_free_object(void) {
                return offsetof(struct drm_driver, gem_free_object);
            }"

            compile_check_conftest "$CODE" "NV_DRM_DRIVER_HAS_GEM_FREE_OBJECT" "" "types"
        ;;

        vga_tryget)
            #
            # Determine if vga_tryget() is present
            #
            # vga_tryget() was removed by commit f369bc3f9096 ("vgaarb: mark
            # vga_tryget static") in v5.9-rc1 (2020-08-01).
            #
            CODE="
            #include <linux/vgaarb.h>
            void conftest_vga_tryget(void) {
                vga_tryget();
            }"

            compile_check_conftest "$CODE" "NV_VGA_TRYGET_PRESENT" "" "functions"
        ;;

        pci_channel_state)
            #
            # Determine if pci_channel_state enum type is present.
            #
            # pci_channel_state was removed by commit 16d79cd4e23b ("PCI: Use
            # 'pci_channel_state_t' instead of 'enum pci_channel_state'") in
            # v5.9-rc1 (2020-07-02).
            #
            CODE="
            #include <linux/pci.h>

            enum pci_channel_state state;
            "

            compile_check_conftest "$CODE" "NV_PCI_CHANNEL_STATE_PRESENT" "" "types"
        ;;

        drm_prime_pages_to_sg_has_drm_device_arg)
            #
            # Determine if drm_prime_pages_to_sg() has 'dev' argument.
            #
            # drm_prime_pages_to_sg() is updated to take 'dev' argument by commit
            # 707d561f77b5 ("drm: allow limiting the scatter list size.").
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif
            #if defined(NV_DRM_DRM_PRIME_H_PRESENT)
            #include <drm/drm_prime.h>
            #endif

            struct sg_table *drm_prime_pages_to_sg(struct drm_device *dev,
                                                   struct page **pages,
                                                   unsigned int nr_pages) {
                return 0;
            }"

            compile_check_conftest "$CODE" "NV_DRM_PRIME_PAGES_TO_SG_HAS_DRM_DEVICE_ARG" "" "types"
        ;;

        drm_driver_has_gem_prime_callbacks)
            #
            # Determine if drm_driver structure has the GEM and PRIME callback
            # function pointers.
            #
            # The GEM and PRIME callback are removed from drm_driver
            # structure, by commit d693def4fd1c ("drm: Remove obsolete GEM and
            # PRIME callbacks from struct drm_driver").
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            #if defined(NV_DRM_DRM_DRV_H_PRESENT)
            #include <drm/drm_drv.h>
            #endif

            void conftest_drm_driver_has_gem_and_prime_callbacks(void) {
                struct drm_driver drv;

                drv.gem_prime_pin = 0;
                drv.gem_prime_get_sg_table = 0;
                drv.gem_prime_vmap = 0;
                drv.gem_prime_vunmap = 0;
                drv.gem_vm_ops = 0;
            }"

            compile_check_conftest "$CODE" "NV_DRM_DRIVER_HAS_GEM_PRIME_CALLBACKS" "" "types"
        ;;

        drm_crtc_atomic_check_has_atomic_state_arg)
            #
            # Determine if drm_crtc_helper_funcs::atomic_check takes 'state'
            # argument of 'struct drm_atomic_state' type.
            #
            # The commit 29b77ad7b9ca ("drm/atomic: Pass the full state to CRTC
            # atomic_check") passed the full atomic state to
            # drm_crtc_helper_funcs::atomic_check()
            #
            # To test the signature of drm_crtc_helper_funcs::atomic_check(),
            # declare a function prototype with typeof ::atomic_check(), and then
            # define the corresponding function implementation with the expected
            # signature.  Successful compilation indicates that ::atomic_check()
            # has the expected signature.
            #
            echo "$CONFTEST_PREAMBLE
            #include <drm/drm_modeset_helper_vtables.h>

            static const struct drm_crtc_helper_funcs *funcs;
            typeof(*funcs->atomic_check) conftest_drm_crtc_atomic_check_has_atomic_state_arg;

            int conftest_drm_crtc_atomic_check_has_atomic_state_arg(
                    struct drm_crtc *crtc, struct drm_atomic_state *state) {
                return 0;
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#define NV_DRM_CRTC_ATOMIC_CHECK_HAS_ATOMIC_STATE_ARG" | append_conftest "types"
            else
                echo "#undef NV_DRM_CRTC_ATOMIC_CHECK_HAS_ATOMIC_STATE_ARG" | append_conftest "types"
            fi
        ;;

        drm_gem_object_vmap_has_map_arg)
            #
            # Determine if drm_gem_object_funcs::vmap takes 'map'
            # argument of 'struct dma_buf_map' type.
            #
            # The commit 49a3f51dfeee ("drm/gem: Use struct dma_buf_map in GEM
            # vmap ops and convert GEM backends") update
            # drm_gem_object_funcs::vmap to take 'map' argument.
            #
            CODE="
            #include <drm/drm_gem.h>
            int conftest_drm_gem_object_vmap_has_map_arg(
                    struct drm_gem_object *obj, struct dma_buf_map *map) {
                return obj->funcs->vmap(obj, map);
            }"

            compile_check_conftest "$CODE" "NV_DRM_GEM_OBJECT_VMAP_HAS_MAP_ARG" "" "types"
        ;;

        unsafe_follow_pfn)
            #
            # Determine if unsafe_follow_pfn() is present.
            #
            # unsafe_follow_pfn() was added by commit 69bacee7f9ad
            # ("mm: Add unsafe_follow_pfn") in v5.13-rc1.
            #
            CODE="
            #include <linux/mm.h>
            void conftest_unsafe_follow_pfn(void) {
                unsafe_follow_pfn();
            }"

            compile_check_conftest "$CODE" "NV_UNSAFE_FOLLOW_PFN_PRESENT" "" "functions"
        ;;

        drm_plane_atomic_check_has_atomic_state_arg)
            #
            # Determine if drm_plane_helper_funcs::atomic_check takes 'state'
            # argument of 'struct drm_atomic_state' type.
            #
            # The commit 7c11b99a8e58 ("drm/atomic: Pass the full state to
            # planes atomic_check") passed the full atomic state to
            # drm_plane_helper_funcs::atomic_check()
            #
            # To test the signature of drm_plane_helper_funcs::atomic_check(),
            # declare a function prototype with typeof ::atomic_check(), and then
            # define the corresponding function implementation with the expected
            # signature.  Successful compilation indicates that ::atomic_check()
            # has the expected signature.
            #
            echo "$CONFTEST_PREAMBLE
            #include <drm/drm_modeset_helper_vtables.h>

            static const struct drm_plane_helper_funcs *funcs;
            typeof(*funcs->atomic_check) conftest_drm_plane_atomic_check_has_atomic_state_arg;

            int conftest_drm_plane_atomic_check_has_atomic_state_arg(
                    struct drm_plane *plane, struct drm_atomic_state *state) {
                return 0;
            }" > conftest$$.c

            $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
            rm -f conftest$$.c

            if [ -f conftest$$.o ]; then
                rm -f conftest$$.o
                echo "#define NV_DRM_PLANE_ATOMIC_CHECK_HAS_ATOMIC_STATE_ARG" | append_conftest "types"
            else
                echo "#undef NV_DRM_PLANE_ATOMIC_CHECK_HAS_ATOMIC_STATE_ARG" | append_conftest "types"
            fi
        ;;

        drm_device_has_pdev)
            #
            # Determine if the 'drm_device' structure has a 'pdev' field.
            #
            # Removed by commit b347e04452ff ("drm: Remove pdev field from
            # struct drm_device") in v5.14-rc1.
            #
            CODE="
            #if defined(NV_DRM_DRMP_H_PRESENT)
            #include <drm/drmP.h>
            #endif

            #if defined(NV_DRM_DRM_DEVICE_H_PRESENT)
            #include <drm/drm_device.h>
            #endif

            int conftest_drm_device_has_pdev(void) {
                return offsetof(struct drm_device, pdev);
            }"

            compile_check_conftest "$CODE" "NV_DRM_DEVICE_HAS_PDEV" "" "types"
        ;;

        acpi_bus_get_device)
            #
            # Determine if the acpi_bus_get_device() function is present
            #
            # acpi_bus_get_device() was removed by commit ac2a3feefad5
            # ("ACPI: bus: Eliminate acpi_bus_get_device()") in
            # v5.18-rc2 (2022-04-05).
            #
            CODE="
            #include <linux/acpi.h>
            int conftest_acpi_bus_get_device(void) {
                return acpi_bus_get_device();
            }"
            compile_check_conftest "$CODE" "NV_ACPI_BUS_GET_DEVICE_PRESENT" "" "functions"
        ;;

        dma_resv_add_fence)
            #
            # Determine if the dma_resv_add_fence() function is present.
            #
            # dma_resv_add_excl_fence() and dma_resv_add_shared_fence() were
            # removed and replaced with dma_resv_add_fence() by commit
            # 73511edf8b19 ("dma-buf: specify usage while adding fences to
            # dma_resv obj v7") in linux-next, expected in v5.19-rc1.
            #
            CODE="
            #if defined(NV_LINUX_DMA_RESV_H_PRESENT)
            #include <linux/dma-resv.h>
            #endif
            void conftest_dma_resv_add_fence(void) {
                dma_resv_add_fence();
            }"

            compile_check_conftest "$CODE" "NV_DMA_RESV_ADD_FENCE_PRESENT" "" "functions"
        ;;

        dma_resv_reserve_fences)
            #
            # Determine if the dma_resv_reserve_fences() function is present.
            #
            # dma_resv_reserve_shared() was removed and replaced with
            # dma_resv_reserve_fences() by commit c8d4c18bfbc4
            # ("dma-buf/drivers: make reserving a shared slot mandatory v4") in
            # linux-next, expected in v5.19-rc1.
            #
            CODE="
            #if defined(NV_LINUX_DMA_RESV_H_PRESENT)
            #include <linux/dma-resv.h>
            #endif
            void conftest_dma_resv_reserve_fences(void) {
                dma_resv_reserve_fences();
            }"

            compile_check_conftest "$CODE" "NV_DMA_RESV_RESERVE_FENCES_PRESENT" "" "functions"
        ;;

        reservation_object_reserve_shared_has_num_fences_arg)
            #
            # Determine if reservation_object_reserve_shared() has 'num_fences'
            # argument.
            #
            # reservation_object_reserve_shared() function prototype was updated
            # to take 'num_fences' argument by commit ca05359f1e64 ("dma-buf:
            # allow reserving more than one shared fence slot") in v4.21-rc1
            # (2018-12-14).
            #
            CODE="
            #include <linux/reservation.h>
            void conftest_reservation_object_reserve_shared_has_num_fences_arg(
                    struct reservation_object *obj,
                    unsigned int num_fences) {
                (void) reservation_object_reserve_shared(obj, num_fences);
            }"

            compile_check_conftest "$CODE" "NV_RESERVATION_OBJECT_RESERVE_SHARED_HAS_NUM_FENCES_ARG" "" "types"
        ;;

        acpi_video_backlight_use_native)
            #
            # Determine if acpi_video_backlight_use_native() function is present
            #
            # acpi_video_backlight_use_native was added by commit 2600bfa3df99
            # (ACPI: video: Add acpi_video_backlight_use_native() helper) for
            # v6.0 (2022-08-17). Note: the include directive for <linux/types.h>
            # in this conftest is necessary in order to support kernels between
            # commit 0b9f7d93ca61 ("ACPI / i915: ignore firmware requests for
            # backlight change") for v3.16 (2014-07-07) and commit 3bd6bce369f5
            # ("ACPI / video: Port to new backlight interface selection API")
            # for v4.2 (2015-07-16). Kernels within this range use the 'bool'
            # type and the related 'false' value in <acpi/video.h> without first
            # including the definitions of that type and value.
            #
            # Building code that includes <acpi/video.h> was broken in a similar
            # manner when building a kernel without ACPI support enabled, for a
            # brief period between commit e92a71624025 on 2010-01-12 ("ACPI:
            # Export EDID blocks to the kernel"), which added a stub function
            # to <acpi/video.h> that returned -ENODEV without including any
            # headers that defined ENODEV (or any headers at all), and commit
            # b72512ed706e on 2010-09-05 ("ACPI: video: fix build for
            # CONFIG_ACPI=n"), which added an <include/errno.h>. Linux 2.6.35
            # and 2.6.36 were released with <acpi/video.h> broken in this way.
            #
            CODE="
            #include <linux/types.h>
            #include <linux/errno.h>
            #include <acpi/video.h>
            void conftest_acpi_video_backglight_use_native(void) {
                acpi_video_backlight_use_native(0);
            }"

            compile_check_conftest "$CODE" "NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE" "" "functions"
        ;;

        # When adding a new conftest entry, please use the correct format for
        # specifying the relevant upstream Linux kernel commit.
        #
        # <function> was added|removed|etc by commit <sha> ("<commit message")
        # in <kernel-version> (<commit date>).

        *)
            # Unknown test name given
            echo "Error: unknown conftest '$1' requested" >&2
            exit 1
        ;;
    esac
}

case "$6" in
    cc_sanity_check)
        #
        # Check if the selected compiler can create object files
        # in the current environment.
        #
        VERBOSE=$7

        echo "int cc_sanity_check(void) {
            return 0;
        }" > conftest$$.c

        $CC -c conftest$$.c > /dev/null 2>&1
        rm -f conftest$$.c

        if [ ! -f conftest$$.o ]; then
            if [ "$VERBOSE" = "full_output" ]; then
                echo "";
            fi
            if [ "$CC" != "cc" ]; then
                echo "The C compiler '$CC' does not appear to be able to"
                echo "create object files.  Please make sure you have "
                echo "your Linux distribution's libc development package"
                echo "installed and that '$CC' is a valid C compiler";
                echo "name."
            else
                echo "The C compiler '$CC' does not appear to be able to"
                echo "create executables.  Please make sure you have "
                echo "your Linux distribution's gcc and libc development"
                echo "packages installed."
            fi
            if [ "$VERBOSE" = "full_output" ]; then
                echo "";
                echo "*** Failed CC sanity check. Bailing out! ***";
                echo "";
            fi
            exit 1
        else
            rm -f conftest$$.o
            exit 0
        fi
    ;;

    cc_version_check)
        #
        # Verify that the same compiler major and minor version is
        # used for the kernel and kernel module.
        #
        # Some gcc version strings that have proven problematic for parsing
        # in the past:
        #
        #  gcc.real (GCC) 3.3 (Debian)
        #  gcc-Version 3.3 (Debian)
        #  gcc (GCC) 3.1.1 20020606 (Debian prerelease)
        #  version gcc 3.2.3
        #
        VERBOSE=$7

        kernel_compile_h=$OUTPUT/include/generated/compile.h

        if [ ! -f ${kernel_compile_h} ]; then
            # The kernel's compile.h file is not present, so there
            # isn't a convenient way to identify the compiler version
            # used to build the kernel.
            IGNORE_CC_MISMATCH=1
        fi

        if [ -n "$IGNORE_CC_MISMATCH" ]; then
            exit 0
        fi

        kernel_cc_string=`cat ${kernel_compile_h} | \
            grep LINUX_COMPILER | cut -f 2 -d '"'`

        kernel_cc_version=`echo ${kernel_cc_string} | grep -o '[0-9]\+\.[0-9]\+' | head -n 1`
        kernel_cc_major=`echo ${kernel_cc_version} | cut -d '.' -f 1`
        kernel_cc_minor=`echo ${kernel_cc_version} | cut -d '.' -f 2`

        echo "
        #if (__GNUC__ != ${kernel_cc_major}) || ((__GNUC__ < 5) && (__GNUC_MINOR__ != ${kernel_cc_minor}))
        #error \"cc version mismatch\"
        #endif
        " > conftest$$.c

        $CC $CFLAGS -c conftest$$.c > /dev/null 2>&1
        rm -f conftest$$.c

        if [ -f conftest$$.o ]; then
            rm -f conftest$$.o
            exit 0;
        else
            #
            # The gcc version check failed
            #

            if [ "$VERBOSE" = "full_output" ]; then
                echo "";
                echo "Compiler version check failed:";
                echo "";
                echo "The major and minor number of the compiler used to";
                echo "compile the kernel:";
                echo "";
                echo "${kernel_cc_string}";
                echo "";
                echo "does not match the compiler used here:";
                echo "";
                $CC --version
                echo "";
                echo "It is recommended to set the CC environment variable";
                echo "to the compiler that was used to compile the kernel.";
                echo ""
                echo "The compiler version check can be disabled by setting";
                echo "the IGNORE_CC_MISMATCH environment variable to \"1\".";
                echo "However, mixing compiler versions between the kernel";
                echo "and kernel modules can result in subtle bugs that are";
                echo "difficult to diagnose.";
                echo "";
                echo "*** Failed CC version check. Bailing out! ***";
                echo "";
            elif [ "$VERBOSE" = "just_msg" ]; then
                echo "The kernel was built with ${kernel_cc_string}, but the" \
                     "current compiler version is `$CC --version | head -n 1`.";
            fi
            exit 1;
        fi
    ;;

    get_uname)
        #
        # Print UTS_RELEASE from the kernel sources, if the kernel header
        # file ../linux/version.h or ../linux/utsrelease.h exists. If
        # neither header file is found, but a Makefile is found, extract
        # PATCHLEVEL and SUBLEVEL, and use them to build the kernel
        # release name.
        #
        # If no source file is found, or if an error occurred, return the
        # output of `uname -r`.
        #
        RET=1
        DIRS="generated linux"
        FILE=""
        
        for DIR in $DIRS; do
            if [ -f $HEADERS/$DIR/utsrelease.h ]; then
                FILE="$HEADERS/$DIR/utsrelease.h"
                break
            elif [ -f $OUTPUT/include/$DIR/utsrelease.h ]; then
                FILE="$OUTPUT/include/$DIR/utsrelease.h"
                break
            fi
        done

        if [ -z "$FILE" ]; then
            if [ -f $HEADERS/linux/version.h ]; then
                FILE="$HEADERS/linux/version.h"
            elif [ -f $OUTPUT/include/linux/version.h ]; then
                FILE="$OUTPUT/include/linux/version.h"
            fi
        fi

        if [ -n "$FILE" ]; then
            #
            # We are either looking at a configured kernel source tree
            # or at headers shipped for a specific kernel.  Determine
            # the kernel version using a CPP check.
            #
            VERSION=`echo "UTS_RELEASE" | $CC - -E -P -include $FILE 2>&1`

            if [ "$?" = "0" -a "VERSION" != "UTS_RELEASE" ]; then
                echo "$VERSION"
                RET=0
            fi
        else
            #
            # If none of the kernel headers ar found, but a Makefile is,
            # extract PATCHLEVEL and SUBLEVEL and use them to find
            # the kernel version.
            #
            MAKEFILE=$HEADERS/../Makefile

            if [ -f $MAKEFILE ]; then
                #
                # This source tree is not configured, but includes
                # the top-level Makefile.
                #
                PATCHLEVEL=$(grep "^PATCHLEVEL =" $MAKEFILE | cut -d " " -f 3)
                SUBLEVEL=$(grep "^SUBLEVEL =" $MAKEFILE | cut -d " " -f 3)

                if [ -n "$PATCHLEVEL" -a -n "$SUBLEVEL" ]; then
                    echo 2.$PATCHLEVEL.$SUBLEVEL
                    RET=0
                fi
            fi
        fi

        if [ "$RET" != "0" ]; then
            uname -r
            exit 1
        else
            exit 0
        fi
    ;;

    xen_sanity_check)
        #
        # Check if the target kernel is a Xen kernel. If so, exit, since
        # the RM doesn't currently support Xen.
        #
        VERBOSE=$7

        if [ -n "$IGNORE_XEN_PRESENCE" -o -n "$VGX_BUILD" ]; then
            exit 0
        fi

        test_xen

        if [ "$XEN_PRESENT" != "0" ]; then
            echo "The kernel you are installing for is a Xen kernel!";
            echo "";
            echo "The NVIDIA driver does not currently support Xen kernels. If ";
            echo "you are using a stock distribution kernel, please install ";
            echo "a variant of this kernel without Xen support; if this is a ";
            echo "custom kernel, please install a standard Linux kernel.  Then ";
            echo "try installing the NVIDIA kernel module again.";
            echo "";
            if [ "$VERBOSE" = "full_output" ]; then
                echo "*** Failed Xen sanity check. Bailing out! ***";
                echo "";
            fi
            exit 1
        else
            exit 0
        fi
    ;;

    preempt_rt_sanity_check)
        #
        # Check if the target kernel has the PREEMPT_RT patch set applied. If
        # so, exit, since the RM doesn't support this configuration.
        #
        VERBOSE=$7

        if [ -n "$IGNORE_PREEMPT_RT_PRESENCE" ]; then
            exit 0
        fi

        if test_configuration_option CONFIG_PREEMPT_RT; then
            PREEMPT_RT_PRESENT=1
        elif test_configuration_option CONFIG_PREEMPT_RT_FULL; then
            PREEMPT_RT_PRESENT=1
        fi

        if [ "$PREEMPT_RT_PRESENT" != "0" ]; then
            echo "The kernel you are installing for is a PREEMPT_RT kernel!";
            echo "";
            echo "The NVIDIA driver does not support real-time kernels. If you ";
            echo "are using a stock distribution kernel, please install ";
            echo "a variant of this kernel that does not have the PREEMPT_RT ";
            echo "patch set applied; if this is a custom kernel, please ";
            echo "install a standard Linux kernel.  Then try installing the ";
            echo "NVIDIA kernel module again.";
            echo "";
            if [ "$VERBOSE" = "full_output" ]; then
                echo "*** Failed PREEMPT_RT sanity check. Bailing out! ***";
                echo "";
            fi
            exit 1
        else
            exit 0
        fi
    ;;

    patch_check)
        #
        # Check for any "official" patches that may have been applied and
        # construct a description table for reporting purposes.
        #
        PATCHES=""

        for PATCH in patch-*.h; do
            if [ -f $PATCH ]; then
                echo "#include \"$PATCH\""
                PATCHES="$PATCHES "`echo $PATCH | sed -s 's/patch-\(.*\)\.h/\1/'`
            fi
        done

        echo "static struct {
                const char *short_description;
                const char *description;
              } __nv_patches[] = {"
            for i in $PATCHES; do
                echo "{ \"$i\", NV_PATCH_${i}_DESCRIPTION },"
            done
        echo "{ NULL, NULL } };"

        exit 0
    ;;

    compile_tests)
        #
        # Run a series of compile tests to determine the set of interfaces
        # and features available in the target kernel.
        #
        shift 6

        CFLAGS=$1
        shift

        for i in $*; do compile_test $i; done

        exit 0
    ;;

    dom0_sanity_check)
        #
        # Determine whether running in DOM0.
        #
        VERBOSE=$7

        if [ -n "$VGX_BUILD" ]; then
            if [ -f /proc/xen/capabilities ]; then
                if [ "`cat /proc/xen/capabilities`" = "control_d" ]; then
                    exit 0
                fi
            else
                echo "The kernel is not running in DOM0.";
                echo "";
                if [ "$VERBOSE" = "full_output" ]; then
                    echo "*** Failed DOM0 sanity check. Bailing out! ***";
                    echo "";
                fi
            fi
            exit 1
        fi
    ;;
    vgpu_kvm_sanity_check)
        #
        # Determine whether we are running a vGPU on KVM host.
        #
        VERBOSE=$7
        iommu=CONFIG_VFIO_IOMMU_TYPE1
        mdev=CONFIG_VFIO_MDEV_DEVICE
        kvm=CONFIG_KVM_VFIO

        if [ -n "$VGX_KVM_BUILD" ]; then
            if (test_configuration_option ${iommu} || test_configuration_option ${iommu}_MODULE) &&
               (test_configuration_option ${mdev} || test_configuration_option ${mdev}_MODULE) &&
               (test_configuration_option ${kvm} || test_configuration_option ${kvm}_MODULE); then
                    exit 0
            else
                echo "The kernel is not running a vGPU on KVM host.";
                echo "";
                if [ "$VERBOSE" = "full_output" ]; then
                    echo "*** Failed vGPU on KVM sanity check. Bailing out! ***";
                    echo "";
                fi
            fi
            exit 1
        else
            exit 0
        fi
    ;;
    test_configuration_option)
        #
        # Check to see if the given config option is set.
        #
        OPTION=$7

        test_configuration_option $OPTION
        exit $?
    ;;

    get_configuration_option)
        #
        # Get the value of the given config option.
        #
        OPTION=$7

        get_configuration_option $OPTION
        exit $?
    ;;


    guess_module_signing_hash)
        #
        # Determine the best cryptographic hash to use for module signing,
        # to the extent that is possible.
        #

        HASH=$(get_configuration_option CONFIG_MODULE_SIG_HASH)

        if [ $? -eq 0 ] && [ -n $HASH ]; then
            echo $HASH
            exit 0
        else
            for SHA in 512 384 256 224 1; do
                if test_configuration_option CONFIG_MODULE_SIG_SHA$SHA; then
                    echo sha$SHA
                    exit 0
                fi
            done
        fi
        exit 1
    ;;


    test_kernel_headers)
        #
        # Check for the availability of certain kernel headers
        #

        test_headers
        exit $?
    ;;


    build_cflags)
        #
        # Generate CFLAGS for use in the compile tests
        #

        build_cflags
        echo $CFLAGS
        exit 0
    ;;

esac

````
### File: `nvidia/nvidia.Kbuild`

````Kbuild
###########################################################################
# Kbuild fragment for nvidia.ko
###########################################################################

#
# Define NVIDIA_{SOURCES,OBJECTS}
#

include $(src)/nvidia/nvidia-sources.Kbuild
NVIDIA_OBJECTS = $(patsubst %.c,%.o,$(NVIDIA_SOURCES))

obj-m += nvidia.o
nvidia-y := $(NVIDIA_OBJECTS)

NVIDIA_KO = nvidia/nvidia.ko


#
# nv-kernel.o_binary is the core binary component of nvidia.ko, shared
# across all UNIX platforms. Create a symlink, "nv-kernel.o" that
# points to nv-kernel.o_binary, and add nv-kernel.o to the list of
# objects to link into nvidia.ko.
#
# Note that:
# - The kbuild "clean" rule will delete all objects in nvidia-y (which
# is why we use a symlink instead of just adding nv-kernel.o_binary
# to nvidia-y).
# - kbuild normally uses the naming convention of ".o_shipped" for
# binary files. That is not used here, because the kbuild rule to
# create the "normal" object file from ".o_shipped" does a copy, not
# a symlink. This file is quite large, so a symlink is preferred.
# - The file added to nvidia-y should be relative to gmake's cwd.
# But, the target for the symlink rule should be prepended with $(obj).
# - The "symlink" command is called using kbuild's if_changed macro to
# generate an .nv-kernel.o.cmd file which can be used on subsequent
# runs to determine if the command line to create the symlink changed
# and needs to be re-executed.
#

NVIDIA_BINARY_OBJECT := $(src)/nvidia/nv-kernel.o_binary
NVIDIA_BINARY_OBJECT_O := nvidia/nv-kernel.o

quiet_cmd_symlink = SYMLINK $@
 cmd_symlink = ln -sf $< $@

targets += $(NVIDIA_BINARY_OBJECT_O)

$(obj)/$(NVIDIA_BINARY_OBJECT_O): $(NVIDIA_BINARY_OBJECT) FORCE
	$(call if_changed,symlink)

nvidia-y += $(NVIDIA_BINARY_OBJECT_O)


#
# Define nvidia.ko-specific CFLAGS.
#

NVIDIA_CFLAGS += -I$(src)/nvidia
NVIDIA_CFLAGS += -DNV_BUILD_MODULE_INSTANCES=0
NVIDIA_CFLAGS += -DNVIDIA_UNDEF_LEGACY_BIT_MACROS
NVIDIA_CFLAGS += -UDEBUG -U_DEBUG -DNDEBUG

$(call ASSIGN_PER_OBJ_CFLAGS, $(NVIDIA_OBJECTS), $(NVIDIA_CFLAGS))


#
# nv-procfs.c requires nv-compiler.h
#

NV_COMPILER_VERSION_HEADER = $(obj)/nv_compiler.h

$(NV_COMPILER_VERSION_HEADER):
	@echo \#define NV_COMPILER \"`$(CC) -v 2>&1 | tail -n 1`\" > $@

$(obj)/nvidia/nv-procfs.o: $(NV_COMPILER_VERSION_HEADER)

clean-files += $(NV_COMPILER_VERSION_HEADER)


#
# Build nv-interface.o from the kernel interface layer objects, suitable
# for further processing by the top-level makefile to produce a precompiled
# kernel interface file.
#

NVIDIA_INTERFACE := nvidia/nv-interface.o

# Linux kernel v5.12 and later looks at "always-y", Linux kernel versions 
# before v5.6 looks at "always"; kernel versions between v5.12 and v5.6
# look at both.

always += $(NVIDIA_INTERFACE)
always-y += $(NVIDIA_INTERFACE)

$(obj)/$(NVIDIA_INTERFACE): $(addprefix $(obj)/,$(NVIDIA_OBJECTS))
	$(LD) -r -o $@ $^


#
# Register the conftests needed by nvidia.ko
#

NV_OBJECTS_DEPEND_ON_CONFTEST += $(NVIDIA_OBJECTS)

NV_CONFTEST_FUNCTION_COMPILE_TESTS += remap_pfn_range
NV_CONFTEST_FUNCTION_COMPILE_TESTS += hash__remap_4k_pfn
NV_CONFTEST_FUNCTION_COMPILE_TESTS += follow_pfn
#NV_CONFTEST_FUNCTION_COMPILE_TESTS += vmap
NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_pages_uc
NV_CONFTEST_FUNCTION_COMPILE_TESTS += list_is_first
NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_memory_uc
NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_memory_array_uc
NV_CONFTEST_FUNCTION_COMPILE_TESTS += change_page_attr
NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_class
NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_choose_state
NV_CONFTEST_FUNCTION_COMPILE_TESTS += vm_insert_page
NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_device_id
NV_CONFTEST_FUNCTION_COMPILE_TESTS += acquire_console_sem
NV_CONFTEST_FUNCTION_COMPILE_TESTS += console_lock
NV_CONFTEST_FUNCTION_COMPILE_TESTS += kmem_cache_create
NV_CONFTEST_FUNCTION_COMPILE_TESTS += on_each_cpu
NV_CONFTEST_FUNCTION_COMPILE_TESTS += smp_call_function
NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer
NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache
NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc
NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace
NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr
NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error
NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table
NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table
NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot
NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages
NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled
NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data
NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data
NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA
NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_remove
NV_CONFTEST_FUNCTION_COMPILE_TESTS += pm_vt_switch_required
NV_CONFTEST_FUNCTION_COMPILE_TESTS += xen_ioemu_inject_msi
NV_CONFTEST_FUNCTION_COMPILE_TESTS += phys_to_dma
NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_dma_ops
NV_CONFTEST_FUNCTION_COMPILE_TESTS += write_cr4
NV_CONFTEST_FUNCTION_COMPILE_TESTS += of_get_property
NV_CONFTEST_FUNCTION_COMPILE_TESTS += of_find_node_by_phandle
NV_CONFTEST_FUNCTION_COMPILE_TESTS += of_node_to_nid
NV_CONFTEST_FUNCTION_COMPILE_TESTS += pnv_pci_get_npu_dev
NV_CONFTEST_FUNCTION_COMPILE_TESTS += for_each_online_node
NV_CONFTEST_FUNCTION_COMPILE_TESTS += node_end_pfn
NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_bus_address
NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_stop_and_remove_bus_device
NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_remove_bus_device
NV_CONFTEST_FUNCTION_COMPILE_TESTS += request_threaded_irq
NV_CONFTEST_FUNCTION_COMPILE_TESTS += register_cpu_notifier
NV_CONFTEST_FUNCTION_COMPILE_TESTS += cpuhp_setup_state
NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_map_resource
NV_CONFTEST_FUNCTION_COMPILE_TESTS += backlight_device_register
NV_CONFTEST_FUNCTION_COMPILE_TESTS += register_acpi_notifier
NV_CONFTEST_FUNCTION_COMPILE_TESTS += timer_setup
NV_CONFTEST_FUNCTION_COMPILE_TESTS += kmem_cache_create_usercopy
NV_CONFTEST_FUNCTION_COMPILE_TESTS += do_gettimeofday
NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_direct_map_resource
NV_CONFTEST_FUNCTION_COMPILE_TESTS += vmf_insert_pfn
NV_CONFTEST_FUNCTION_COMPILE_TESTS += jiffies_to_timespec
NV_CONFTEST_FUNCTION_COMPILE_TESTS += ktime_get_raw_ts64
NV_CONFTEST_FUNCTION_COMPILE_TESTS += ktime_get_real_ts64
NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_nocache
NV_CONFTEST_FUNCTION_COMPILE_TESTS += vga_tryget
NV_CONFTEST_FUNCTION_COMPILE_TESTS += unsafe_follow_pfn
NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_bus_get_device
NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_video_backlight_use_native

NV_CONFTEST_SYMBOL_COMPILE_TESTS += is_export_symbol_gpl_of_node_to_nid
NV_CONFTEST_SYMBOL_COMPILE_TESTS += is_export_symbol_present_swiotlb_map_sg_attrs
NV_CONFTEST_SYMBOL_COMPILE_TESTS += is_export_symbol_present_swiotlb_dma_ops

NV_CONFTEST_TYPE_COMPILE_TESTS += i2c_adapter
NV_CONFTEST_TYPE_COMPILE_TESTS += pm_message_t
NV_CONFTEST_TYPE_COMPILE_TESTS += irq_handler_t
NV_CONFTEST_TYPE_COMPILE_TESTS += acpi_device_ops
NV_CONFTEST_TYPE_COMPILE_TESTS += acpi_op_remove
NV_CONFTEST_TYPE_COMPILE_TESTS += acpi_device_id
NV_CONFTEST_TYPE_COMPILE_TESTS += outer_flush_all
NV_CONFTEST_TYPE_COMPILE_TESTS += proc_dir_entry
NV_CONFTEST_TYPE_COMPILE_TESTS += scatterlist
NV_CONFTEST_TYPE_COMPILE_TESTS += sg_table
NV_CONFTEST_TYPE_COMPILE_TESTS += file_operations
NV_CONFTEST_TYPE_COMPILE_TESTS += vm_operations_struct
NV_CONFTEST_TYPE_COMPILE_TESTS += atomic_long_type
NV_CONFTEST_TYPE_COMPILE_TESTS += pci_save_state
NV_CONFTEST_TYPE_COMPILE_TESTS += file_inode
NV_CONFTEST_TYPE_COMPILE_TESTS += task_struct
NV_CONFTEST_TYPE_COMPILE_TESTS += kuid_t
NV_CONFTEST_TYPE_COMPILE_TESTS += dma_ops
NV_CONFTEST_TYPE_COMPILE_TESTS += swiotlb_dma_ops
NV_CONFTEST_TYPE_COMPILE_TESTS += dma_map_ops
NV_CONFTEST_TYPE_COMPILE_TESTS += noncoherent_swiotlb_dma_ops
NV_CONFTEST_TYPE_COMPILE_TESTS += vm_fault_present
NV_CONFTEST_TYPE_COMPILE_TESTS += vm_fault_has_address
NV_CONFTEST_TYPE_COMPILE_TESTS += kernel_write
NV_CONFTEST_TYPE_COMPILE_TESTS += strnstr
NV_CONFTEST_TYPE_COMPILE_TESTS += iterate_dir
NV_CONFTEST_TYPE_COMPILE_TESTS += kstrtoull
NV_CONFTEST_TYPE_COMPILE_TESTS += backlight_properties_type
NV_CONFTEST_TYPE_COMPILE_TESTS += proc_ops
NV_CONFTEST_TYPE_COMPILE_TESTS += timeval
NV_CONFTEST_TYPE_COMPILE_TESTS += mm_has_mmap_lock
NV_CONFTEST_TYPE_COMPILE_TESTS += kmem_cache_has_kobj_remove_work
NV_CONFTEST_TYPE_COMPILE_TESTS += sysfs_slab_unlink
NV_CONFTEST_TYPE_COMPILE_TESTS += vmalloc_has_pgprot_t_arg
NV_CONFTEST_TYPE_COMPILE_TESTS += pci_dev_has_skip_bus_pm
NV_CONFTEST_TYPE_COMPILE_TESTS += pci_channel_state

NV_CONFTEST_GENERIC_COMPILE_TESTS += dom0_kernel_present
NV_CONFTEST_GENERIC_COMPILE_TESTS += nvidia_vgpu_kvm_build
NV_CONFTEST_GENERIC_COMPILE_TESTS += nvidia_grid_build
NV_CONFTEST_GENERIC_COMPILE_TESTS += get_user_pages
NV_CONFTEST_GENERIC_COMPILE_TESTS += get_user_pages_remote
NV_CONFTEST_GENERIC_COMPILE_TESTS += list_cut_position
NV_CONFTEST_GENERIC_COMPILE_TESTS += vm_fault_t

NV_CONFTEST_MACRO_COMPILE_TESTS += INIT_WORK

````

## Full Trace Log

````log

Found 2 patch operation(s) to perform.
Fuzzy matching enabled with threshold: 0.70
debug: apply_patches_to_dir: applying 2 patch(es) to '.' (dry_run=true, fuzz=0.70)
debug:   [1/2] Applying patch for 'conftest.sh' (1 hunk(s))
Applying patch to: conftest.sh
debug:   apply_patch_to_file: target_dir='.', hunks=1, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'conftest.sh'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("conftest.sh")' on virtual path '<TARGET_DIR>'
trace:   Path safety verified: 'conftest.sh' safely resolves to '<TARGET_DIR>/conftest.sh'
debug:   Resolved safe target path: '<TARGET_DIR>/conftest.sh'
debug:   Target file exists: '<TARGET_DIR>/conftest.sh'. Reading content...
trace:     Read 179062 bytes (5090 lines) from target file.
debug:   Applying patch logic to content in-memory...
debug: apply_patch_to_content: patch for 'conftest.sh' (1 hunks), original content: 179062 bytes
debug:   apply_patch_to_lines called with 5090 lines of original content.
debug: resolve_hunk_line_hints: evaluating 1 hunk(s) across 5090 target lines
trace: Hunk::get_match_block: extracted 5 match line(s)
trace: is_low_entropy_line: line '' is low-entropy
trace:   Hunk 1: already has explicit line hint 4646
trace: resolve_hunk_line_hints: beginning relaxation pass 1
debug: resolve_hunk_line_hints: completed hint resolution. 1/1 hunk(s) have anchors.
debug: HunkApplier: initialized with 1 hunk(s) across 5090 line(s) of target content (fuzz_factor=0.70, dry_run=true)
trace: HunkApplier::set_original_newline_status: original_ends_with_newline=true
debug: apply_hunk_to_lines: applying hunk with 17 line(s) against target with 5090 line(s)
trace: Hunk::get_match_block: extracted 5 match line(s)
trace:   Match block: ["", "            compile_check_conftest \"$CODE\" \"NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE\" \"\" \"functions\"", "        ;;", "    esac", "}"]
trace: Hunk::get_replace_block: extracted 17 replacement line(s)
trace:   Replace block: ["", "            compile_check_conftest \"$CODE\" \"NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE\" \"\" \"functions\"", "        ;;", "", "        # When adding a new conftest entry, please use the correct format for", "        # specifying the relevant upstream Linux kernel commit.", "        #", "        # <function> was added|removed|etc by commit <sha> (\"<commit message\")", "        # in <kernel-version> (<commit date>).", "", "        *)", "            # Unknown test name given", "            echo \"Error: unknown conftest '$1' requested\" >&2", "            exit 1", "        ;;", "    esac", "}"]
trace: Hunk::has_changes: true
trace: Hunk::get_match_block: extracted 5 match line(s)
trace: Hunk::required_match_span: calculated required match span as 1 line(s) (first_match_idx=Some(2), last_match_idx=Some(2))
trace: DefaultHunkFinder::find_candidate_locations: match block len=5, required_match_span=1, target lines=5090
trace: is_low_entropy_line: line '' is low-entropy
trace:   find_hunk_location_internal: match_block has 5 lines (entropy=true), target has 5090 lines
trace:   find_hunk_location_internal called for a hunk with 5 lines to match against 5090 target lines.
trace:     Attempting exact match for hunk (match block has 5 line(s))...
trace: tie_break_with_line_number: strategy='exact', hint=Some(4646), entropy=true
trace:       No exact matches found.
trace:     Strategy 1 (Exact): no exact match found.
trace:     Attempting exact match (ignoring trailing whitespace) for hunk (match block has 5 line(s))...
trace: tie_break_with_line_number: strategy='exact (ignoring whitespace)', hint=Some(4646), entropy=true
trace:       No exact (ignoring whitespace) matches found.
trace:     Strategy 2 (Whitespace-insensitive): no match found.
debug:     Strategy 3 (Fuzzy): beginning flexible window fuzzy search (threshold=0.70, match block len=0.7)
trace:       Hunk match block (5 lines): ["", "            compile_check_conftest \"$CODE\" \"NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE\" \"\" \"functions\"", "        ;;", "    esac", "}"]
trace:       Searching with window sizes from 2 to 27 (hunk size: 5, fuzz distance: 22)
debug:       find_search_ranges: analyzing 5 match line(s) against 5090 target line(s).
trace:         Identified 1 high-entropy candidate anchor line(s) (search_radius=15, max candidates to test=100)
debug:       Found anchor line (hunk line 2) with 1 occurrences.
trace:         Anchor text: 'compile_check_conftest "$CODE" "NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE" "" "functions"'
trace:         Occurrence at target line 4647: window estimated [4631..4687] (search radius +/-15)
trace:         Raw ranges before merging: [(4630, 4687)]
trace: merge_ranges: merging 1 input range(s): [(4630, 4687)]
trace: merge_ranges: result 1 disjoint range(s): [(4630, 4687)]
debug:       Search ranges merged: 1 disjoint range(s) covering 57/5090 line(s) (98.9% pruned): [(4630, 4687)]
trace:     Using search ranges: [(4630, 4687)]
debug:       compute_scored_windows (parallel): evaluating 1131 candidate window(s) across 1 range(s) (window lengths 2..=27)
trace:         Match block length: 5, Target line count: 5090, Search ranges: [(4630, 4687)]
trace:         score_window: window_len=5, match_len=5, line_score=0.600, ratio_lines=0.600, final_score=0.600
trace:         score_window: window_len=4, match_len=5, line_score=0.667, ratio_lines=0.667, final_score=0.667
trace:         score_window: window_len=6, match_len=5, line_score=0.594, ratio_lines=0.545, final_score=0.594
trace:         score_window: window_len=3, match_len=5, line_score=0.500, ratio_lines=0.500, final_score=0.500
trace:         score_window: window_len=2, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.203
trace:         score_window: window_len=18, match_len=5, line_score=0.522, ratio_lines=0.261, final_score=0.522
trace:         score_window: window_len=19, match_len=5, line_score=0.516, ratio_lines=0.250, final_score=0.516
trace:         score_window: window_len=20, match_len=5, line_score=0.510, ratio_lines=0.240, final_score=0.510
trace:         score_window: window_len=21, match_len=5, line_score=0.504, ratio_lines=0.231, final_score=0.504
trace:         score_window: window_len=7, match_len=5, line_score=0.588, ratio_lines=0.500, final_score=0.588
trace:         score_window: window_len=2, match_len=5, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=22, match_len=5, line_score=0.498, ratio_lines=0.222, final_score=0.498
trace:         score_window: window_len=8, match_len=5, line_score=0.582, ratio_lines=0.462, final_score=0.582
trace:         score_window: window_len=9, match_len=5, line_score=0.576, ratio_lines=0.429, final_score=0.576
trace:         score_window: window_len=23, match_len=5, line_score=0.492, ratio_lines=0.214, final_score=0.492
trace:         score_window: window_len=10, match_len=5, line_score=0.570, ratio_lines=0.400, final_score=0.570
trace:         score_window: window_len=2, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.158
trace:         score_window: window_len=17, match_len=5, line_score=0.528, ratio_lines=0.273, final_score=0.528
trace:         score_window: window_len=18, match_len=5, line_score=0.522, ratio_lines=0.261, final_score=0.522
trace:         score_window: window_len=19, match_len=5, line_score=0.516, ratio_lines=0.250, final_score=0.516
trace:         score_window: window_len=11, match_len=5, line_score=0.564, ratio_lines=0.375, final_score=0.564
trace:         score_window: window_len=20, match_len=5, line_score=0.510, ratio_lines=0.240, final_score=0.510
trace:         score_window: window_len=12, match_len=5, line_score=0.558, ratio_lines=0.353, final_score=0.558
trace:         score_window: window_len=21, match_len=5, line_score=0.504, ratio_lines=0.231, final_score=0.504
trace:         score_window: window_len=13, match_len=5, line_score=0.552, ratio_lines=0.333, final_score=0.552
trace:         score_window: window_len=22, match_len=5, line_score=0.498, ratio_lines=0.222, final_score=0.498
trace:         score_window: window_len=14, match_len=5, line_score=0.546, ratio_lines=0.316, final_score=0.546
trace:         score_window: window_len=15, match_len=5, line_score=0.540, ratio_lines=0.300, final_score=0.540
trace:         score_window: window_len=23, match_len=5, line_score=0.492, ratio_lines=0.214, final_score=0.492
trace:         score_window: window_len=16, match_len=5, line_score=0.534, ratio_lines=0.286, final_score=0.534
trace:         score_window: window_len=17, match_len=5, line_score=0.528, ratio_lines=0.273, final_score=0.528
trace:         score_window: window_len=18, match_len=5, line_score=0.522, ratio_lines=0.261, final_score=0.522
trace:         score_window: window_len=19, match_len=5, line_score=0.516, ratio_lines=0.250, final_score=0.516
trace:         score_window: window_len=20, match_len=5, line_score=0.510, ratio_lines=0.240, final_score=0.510
trace:         score_window: window_len=21, match_len=5, line_score=0.504, ratio_lines=0.231, final_score=0.504
trace:         score_window: window_len=22, match_len=5, line_score=0.498, ratio_lines=0.222, final_score=0.498
trace:         score_window: window_len=23, match_len=5, line_score=0.492, ratio_lines=0.214, final_score=0.492
trace:         score_window: window_len=2, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.186
trace:         score_window: window_len=5, match_len=5, line_score=0.600, ratio_lines=0.600, final_score=0.600
trace:         score_window: window_len=4, match_len=5, line_score=0.667, ratio_lines=0.667, final_score=0.667
trace:         score_window: window_len=6, match_len=5, line_score=0.594, ratio_lines=0.545, final_score=0.594
trace:         score_window: window_len=7, match_len=5, line_score=0.588, ratio_lines=0.500, final_score=0.588
trace:         score_window: window_len=16, match_len=5, line_score=0.534, ratio_lines=0.286, final_score=0.534
trace:         score_window: window_len=2, match_len=5, line_score=0.571, ratio_lines=0.571, final_score=0.571
trace:         score_window: window_len=8, match_len=5, line_score=0.582, ratio_lines=0.462, final_score=0.582
trace:         score_window: window_len=17, match_len=5, line_score=0.528, ratio_lines=0.273, final_score=0.528
trace:         score_window: window_len=9, match_len=5, line_score=0.576, ratio_lines=0.429, final_score=0.576
trace:         score_window: window_len=18, match_len=5, line_score=0.522, ratio_lines=0.261, final_score=0.522
trace:         score_window: window_len=10, match_len=5, line_score=0.570, ratio_lines=0.400, final_score=0.570
trace:         score_window: window_len=19, match_len=5, line_score=0.516, ratio_lines=0.250, final_score=0.516
trace:         score_window: window_len=11, match_len=5, line_score=0.564, ratio_lines=0.375, final_score=0.564
trace:         score_window: window_len=20, match_len=5, line_score=0.510, ratio_lines=0.240, final_score=0.510
trace:         score_window: window_len=12, match_len=5, line_score=0.558, ratio_lines=0.353, final_score=0.558
trace:         score_window: window_len=13, match_len=5, line_score=0.552, ratio_lines=0.333, final_score=0.552
trace:         score_window: window_len=21, match_len=5, line_score=0.504, ratio_lines=0.231, final_score=0.504
trace:         score_window: window_len=14, match_len=5, line_score=0.546, ratio_lines=0.316, final_score=0.546
trace:         score_window: window_len=15, match_len=5, line_score=0.540, ratio_lines=0.300, final_score=0.540
trace:         score_window: window_len=22, match_len=5, line_score=0.498, ratio_lines=0.222, final_score=0.498
trace:         score_window: window_len=16, match_len=5, line_score=0.534, ratio_lines=0.286, final_score=0.534
trace:         score_window: window_len=17, match_len=5, line_score=0.528, ratio_lines=0.273, final_score=0.528
trace:         score_window: window_len=23, match_len=5, line_score=0.492, ratio_lines=0.214, final_score=0.492
trace:         score_window: window_len=18, match_len=5, line_score=0.522, ratio_lines=0.261, final_score=0.522
trace:         score_window: window_len=19, match_len=5, line_score=0.516, ratio_lines=0.250, final_score=0.516
trace:         score_window: window_len=2, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.144
trace:         score_window: window_len=20, match_len=5, line_score=0.510, ratio_lines=0.240, final_score=0.510
trace:         score_window: window_len=14, match_len=5, line_score=0.364, ratio_lines=0.211, final_score=0.364
trace:         score_window: window_len=21, match_len=5, line_score=0.504, ratio_lines=0.231, final_score=0.504
trace:         score_window: window_len=15, match_len=5, line_score=0.540, ratio_lines=0.300, final_score=0.540
trace:         score_window: window_len=22, match_len=5, line_score=0.498, ratio_lines=0.222, final_score=0.498
trace:         score_window: window_len=16, match_len=5, line_score=0.534, ratio_lines=0.286, final_score=0.534
trace:         score_window: window_len=23, match_len=5, line_score=0.492, ratio_lines=0.214, final_score=0.492
trace:         score_window: window_len=5, match_len=5, line_score=0.400, ratio_lines=0.400, final_score=0.400
trace:         score_window: window_len=17, match_len=5, line_score=0.528, ratio_lines=0.273, final_score=0.528
trace:         score_window: window_len=4, match_len=5, line_score=0.444, ratio_lines=0.444, final_score=0.444
trace:         score_window: window_len=6, match_len=5, line_score=0.396, ratio_lines=0.364, final_score=0.396
trace:         score_window: window_len=3, match_len=5, line_score=0.500, ratio_lines=0.500, final_score=0.500
trace:         score_window: window_len=18, match_len=5, line_score=0.522, ratio_lines=0.261, final_score=0.522
trace:         score_window: window_len=7, match_len=5, line_score=0.392, ratio_lines=0.333, final_score=0.392
trace:         score_window: window_len=2, match_len=5, line_score=0.571, ratio_lines=0.571, final_score=0.571
trace:         score_window: window_len=19, match_len=5, line_score=0.516, ratio_lines=0.250, final_score=0.516
trace:         score_window: window_len=8, match_len=5, line_score=0.388, ratio_lines=0.308, final_score=0.388
trace:         score_window: window_len=20, match_len=5, line_score=0.510, ratio_lines=0.240, final_score=0.510
trace:         score_window: window_len=9, match_len=5, line_score=0.384, ratio_lines=0.286, final_score=0.384
trace:         score_window: window_len=21, match_len=5, line_score=0.504, ratio_lines=0.231, final_score=0.504
trace:         score_window: window_len=10, match_len=5, line_score=0.380, ratio_lines=0.267, final_score=0.380
trace:         score_window: window_len=22, match_len=5, line_score=0.498, ratio_lines=0.222, final_score=0.498
trace:         score_window: window_len=11, match_len=5, line_score=0.376, ratio_lines=0.250, final_score=0.376
trace:         score_window: window_len=23, match_len=5, line_score=0.492, ratio_lines=0.214, final_score=0.492
trace:         score_window: window_len=12, match_len=5, line_score=0.372, ratio_lines=0.235, final_score=0.372
trace:         score_window: window_len=13, match_len=5, line_score=0.368, ratio_lines=0.222, final_score=0.368
trace:         score_window: window_len=14, match_len=5, line_score=0.364, ratio_lines=0.211, final_score=0.364
trace:         score_window: window_len=2, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.169
trace:         score_window: window_len=13, match_len=5, line_score=0.368, ratio_lines=0.222, final_score=0.368
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.222
trace:         score_window: window_len=14, match_len=5, line_score=0.546, ratio_lines=0.316, final_score=0.546
trace:         score_window: window_len=6, match_len=5, line_score=0.198, ratio_lines=0.182, final_score=0.198
trace:         score_window: window_len=3, match_len=5, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=15, match_len=5, line_score=0.540, ratio_lines=0.300, final_score=0.540
trace:         score_window: window_len=7, match_len=5, line_score=0.196, ratio_lines=0.167, final_score=0.196
trace:         score_window: window_len=2, match_len=5, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=16, match_len=5, line_score=0.534, ratio_lines=0.286, final_score=0.534
trace:         score_window: window_len=8, match_len=5, line_score=0.194, ratio_lines=0.154, final_score=0.194
trace:         score_window: window_len=17, match_len=5, line_score=0.528, ratio_lines=0.273, final_score=0.528
trace:         score_window: window_len=9, match_len=5, line_score=0.192, ratio_lines=0.143, final_score=0.192
trace:         score_window: window_len=18, match_len=5, line_score=0.522, ratio_lines=0.261, final_score=0.522
trace:         score_window: window_len=10, match_len=5, line_score=0.190, ratio_lines=0.133, final_score=0.190
trace:         score_window: window_len=19, match_len=5, line_score=0.516, ratio_lines=0.250, final_score=0.516
trace:         score_window: window_len=20, match_len=5, line_score=0.510, ratio_lines=0.240, final_score=0.510
trace:         score_window: window_len=21, match_len=5, line_score=0.504, ratio_lines=0.231, final_score=0.504
trace:         score_window: window_len=5, match_len=5, line_score=0.200, ratio_lines=0.200, final_score=0.243
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.336
trace:         score_window: window_len=22, match_len=5, line_score=0.498, ratio_lines=0.222, final_score=0.498
trace:         score_window: window_len=6, match_len=5, line_score=0.198, ratio_lines=0.182, final_score=0.205
trace:         score_window: window_len=3, match_len=5, line_score=0.250, ratio_lines=0.250, final_score=0.308
trace:         score_window: window_len=23, match_len=5, line_score=0.492, ratio_lines=0.214, final_score=0.492
trace:         score_window: window_len=7, match_len=5, line_score=0.196, ratio_lines=0.167, final_score=0.196
trace:         score_window: window_len=2, match_len=5, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=27, match_len=5, line_score=0.624, ratio_lines=0.250, final_score=0.624
trace:         score_window: window_len=8, match_len=5, line_score=0.194, ratio_lines=0.154, final_score=0.194
trace:         score_window: window_len=4, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.172
trace:         score_window: window_len=9, match_len=5, line_score=0.192, ratio_lines=0.143, final_score=0.192
trace:         score_window: window_len=3, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.153
trace:         score_window: window_len=2, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.154
trace:         score_window: window_len=5, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.157
trace:         score_window: window_len=12, match_len=5, line_score=0.372, ratio_lines=0.235, final_score=0.372
trace:         score_window: window_len=4, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.158
trace:         score_window: window_len=13, match_len=5, line_score=0.552, ratio_lines=0.333, final_score=0.552
trace:         score_window: window_len=14, match_len=5, line_score=0.546, ratio_lines=0.316, final_score=0.546
trace:         score_window: window_len=6, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.156
trace:         score_window: window_len=15, match_len=5, line_score=0.540, ratio_lines=0.300, final_score=0.540
trace:         score_window: window_len=7, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.157
trace:         score_window: window_len=16, match_len=5, line_score=0.534, ratio_lines=0.286, final_score=0.534
trace:         score_window: window_len=8, match_len=5, line_score=0.194, ratio_lines=0.154, final_score=0.194
trace:         score_window: window_len=17, match_len=5, line_score=0.528, ratio_lines=0.273, final_score=0.528
trace:         score_window: window_len=18, match_len=5, line_score=0.522, ratio_lines=0.261, final_score=0.522
trace:         score_window: window_len=5, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.165
trace:         score_window: window_len=19, match_len=5, line_score=0.516, ratio_lines=0.250, final_score=0.516
trace:         score_window: window_len=4, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.166
trace:         score_window: window_len=20, match_len=5, line_score=0.510, ratio_lines=0.240, final_score=0.510
trace:         score_window: window_len=6, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.165
trace:         score_window: window_len=21, match_len=5, line_score=0.504, ratio_lines=0.231, final_score=0.504
trace:         score_window: window_len=3, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.169
trace:         score_window: window_len=22, match_len=5, line_score=0.498, ratio_lines=0.222, final_score=0.498
trace:         score_window: window_len=7, match_len=5, line_score=0.196, ratio_lines=0.167, final_score=0.196
trace:         score_window: window_len=23, match_len=5, line_score=0.492, ratio_lines=0.214, final_score=0.492
trace:         score_window: window_len=8, match_len=5, line_score=0.194, ratio_lines=0.154, final_score=0.194
trace:         score_window: window_len=26, match_len=5, line_score=0.632, ratio_lines=0.258, final_score=0.632
trace:         score_window: window_len=9, match_len=5, line_score=0.192, ratio_lines=0.143, final_score=0.192
trace:         score_window: window_len=5, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.176
trace:         score_window: window_len=4, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.189
trace:         score_window: window_len=5, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.220
trace:         score_window: window_len=6, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.167
trace:         score_window: window_len=4, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.200
trace:         score_window: window_len=3, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.146
trace:         score_window: window_len=2, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.076
trace:         score_window: window_len=6, match_len=5, line_score=0.198, ratio_lines=0.182, final_score=0.270
trace:         score_window: window_len=11, match_len=5, line_score=0.376, ratio_lines=0.250, final_score=0.376
trace:         score_window: window_len=12, match_len=5, line_score=0.558, ratio_lines=0.353, final_score=0.558
trace:         score_window: window_len=3, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.182
trace:         score_window: window_len=13, match_len=5, line_score=0.552, ratio_lines=0.333, final_score=0.552
trace:         score_window: window_len=14, match_len=5, line_score=0.546, ratio_lines=0.316, final_score=0.546
trace:         score_window: window_len=7, match_len=5, line_score=0.196, ratio_lines=0.167, final_score=0.240
trace:         score_window: window_len=15, match_len=5, line_score=0.540, ratio_lines=0.300, final_score=0.540
trace:         score_window: window_len=8, match_len=5, line_score=0.194, ratio_lines=0.154, final_score=0.224
trace:         score_window: window_len=16, match_len=5, line_score=0.534, ratio_lines=0.286, final_score=0.534
trace:         score_window: window_len=17, match_len=5, line_score=0.528, ratio_lines=0.273, final_score=0.528
trace:         score_window: window_len=9, match_len=5, line_score=0.192, ratio_lines=0.143, final_score=0.205
trace:         score_window: window_len=18, match_len=5, line_score=0.522, ratio_lines=0.261, final_score=0.522
trace:         score_window: window_len=10, match_len=5, line_score=0.190, ratio_lines=0.133, final_score=0.200
trace:         score_window: window_len=19, match_len=5, line_score=0.516, ratio_lines=0.250, final_score=0.516
trace:         score_window: window_len=20, match_len=5, line_score=0.510, ratio_lines=0.240, final_score=0.510
trace:         score_window: window_len=5, match_len=5, line_score=0.200, ratio_lines=0.200, final_score=0.284
trace:         score_window: window_len=21, match_len=5, line_score=0.504, ratio_lines=0.231, final_score=0.504
trace:         score_window: window_len=4, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.200
trace:         score_window: window_len=22, match_len=5, line_score=0.498, ratio_lines=0.222, final_score=0.498
trace:         score_window: window_len=6, match_len=5, line_score=0.198, ratio_lines=0.182, final_score=0.226
trace:         score_window: window_len=23, match_len=5, line_score=0.492, ratio_lines=0.214, final_score=0.492
trace:         score_window: window_len=3, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.182
trace:         score_window: window_len=25, match_len=5, line_score=0.640, ratio_lines=0.267, final_score=0.640
trace:         score_window: window_len=7, match_len=5, line_score=0.196, ratio_lines=0.167, final_score=0.234
trace:         score_window: window_len=5, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.181
trace:         score_window: window_len=2, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.183
trace:         score_window: window_len=6, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.184
trace:         score_window: window_len=10, match_len=5, line_score=0.380, ratio_lines=0.267, final_score=0.380
trace:         score_window: window_len=8, match_len=5, line_score=0.194, ratio_lines=0.154, final_score=0.213
trace:         score_window: window_len=11, match_len=5, line_score=0.564, ratio_lines=0.375, final_score=0.564
trace:         score_window: window_len=12, match_len=5, line_score=0.558, ratio_lines=0.353, final_score=0.558
trace:         score_window: window_len=13, match_len=5, line_score=0.552, ratio_lines=0.333, final_score=0.552
trace:         score_window: window_len=9, match_len=5, line_score=0.192, ratio_lines=0.143, final_score=0.208
trace:         score_window: window_len=14, match_len=5, line_score=0.546, ratio_lines=0.316, final_score=0.546
trace:         score_window: window_len=15, match_len=5, line_score=0.540, ratio_lines=0.300, final_score=0.540
trace:         score_window: window_len=5, match_len=5, line_score=0.200, ratio_lines=0.200, final_score=0.244
trace:         score_window: window_len=16, match_len=5, line_score=0.534, ratio_lines=0.286, final_score=0.534
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.338
trace:         score_window: window_len=17, match_len=5, line_score=0.528, ratio_lines=0.273, final_score=0.528
trace:         score_window: window_len=6, match_len=5, line_score=0.198, ratio_lines=0.182, final_score=0.198
trace:         score_window: window_len=18, match_len=5, line_score=0.522, ratio_lines=0.261, final_score=0.522
trace:         score_window: window_len=7, match_len=5, line_score=0.196, ratio_lines=0.167, final_score=0.224
trace:         score_window: window_len=19, match_len=5, line_score=0.516, ratio_lines=0.250, final_score=0.516
trace:         score_window: window_len=8, match_len=5, line_score=0.194, ratio_lines=0.154, final_score=0.222
trace:         score_window: window_len=20, match_len=5, line_score=0.510, ratio_lines=0.240, final_score=0.510
trace:         score_window: window_len=9, match_len=5, line_score=0.192, ratio_lines=0.143, final_score=0.251
trace:         score_window: window_len=21, match_len=5, line_score=0.504, ratio_lines=0.231, final_score=0.504
trace:         score_window: window_len=10, match_len=5, line_score=0.190, ratio_lines=0.133, final_score=0.233
trace:         score_window: window_len=22, match_len=5, line_score=0.498, ratio_lines=0.222, final_score=0.498
trace:         score_window: window_len=23, match_len=5, line_score=0.492, ratio_lines=0.214, final_score=0.492
trace:         score_window: window_len=11, match_len=5, line_score=0.188, ratio_lines=0.125, final_score=0.232
trace:         score_window: window_len=24, match_len=5, line_score=0.648, ratio_lines=0.276, final_score=0.648
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.274
trace:         score_window: window_len=6, match_len=5, line_score=0.198, ratio_lines=0.182, final_score=0.282
trace:         score_window: window_len=3, match_len=5, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=5, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.200
trace:         score_window: window_len=7, match_len=5, line_score=0.196, ratio_lines=0.167, final_score=0.308
trace:         score_window: window_len=4, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.193
trace:         score_window: window_len=9, match_len=5, line_score=0.384, ratio_lines=0.286, final_score=0.384
trace:         score_window: window_len=10, match_len=5, line_score=0.570, ratio_lines=0.400, final_score=0.570
trace:         score_window: window_len=8, match_len=5, line_score=0.194, ratio_lines=0.154, final_score=0.255
trace:         score_window: window_len=11, match_len=5, line_score=0.564, ratio_lines=0.375, final_score=0.564
trace:         score_window: window_len=12, match_len=5, line_score=0.558, ratio_lines=0.353, final_score=0.558
trace:         score_window: window_len=9, match_len=5, line_score=0.192, ratio_lines=0.143, final_score=0.235
trace:         score_window: window_len=13, match_len=5, line_score=0.552, ratio_lines=0.333, final_score=0.552
trace:         score_window: window_len=14, match_len=5, line_score=0.546, ratio_lines=0.316, final_score=0.546
trace:         score_window: window_len=10, match_len=5, line_score=0.190, ratio_lines=0.133, final_score=0.234
trace:         score_window: window_len=15, match_len=5, line_score=0.540, ratio_lines=0.300, final_score=0.540
trace:         score_window: window_len=16, match_len=5, line_score=0.534, ratio_lines=0.286, final_score=0.534
trace:         score_window: window_len=11, match_len=5, line_score=0.188, ratio_lines=0.125, final_score=0.209
trace:         score_window: window_len=17, match_len=5, line_score=0.528, ratio_lines=0.273, final_score=0.528
trace:         score_window: window_len=18, match_len=5, line_score=0.522, ratio_lines=0.261, final_score=0.522
trace:         score_window: window_len=5, match_len=5, line_score=0.200, ratio_lines=0.200, final_score=0.227
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.222
trace:         score_window: window_len=19, match_len=5, line_score=0.516, ratio_lines=0.250, final_score=0.516
trace:         score_window: window_len=6, match_len=5, line_score=0.198, ratio_lines=0.182, final_score=0.225
trace:         score_window: window_len=3, match_len=5, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=20, match_len=5, line_score=0.510, ratio_lines=0.240, final_score=0.510
trace:         score_window: window_len=7, match_len=5, line_score=0.196, ratio_lines=0.167, final_score=0.258
trace:         score_window: window_len=2, match_len=5, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=21, match_len=5, line_score=0.504, ratio_lines=0.231, final_score=0.504
trace:         score_window: window_len=8, match_len=5, line_score=0.194, ratio_lines=0.154, final_score=0.237
trace:         score_window: window_len=22, match_len=5, line_score=0.498, ratio_lines=0.222, final_score=0.498
trace:         score_window: window_len=9, match_len=5, line_score=0.192, ratio_lines=0.143, final_score=0.236
trace:         score_window: window_len=23, match_len=5, line_score=0.656, ratio_lines=0.286, final_score=0.656
trace:         score_window: window_len=10, match_len=5, line_score=0.190, ratio_lines=0.133, final_score=0.211
trace:         score_window: window_len=4, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.206
trace:         score_window: window_len=3, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.176
trace:         score_window: window_len=8, match_len=5, line_score=0.388, ratio_lines=0.308, final_score=0.390
trace:         score_window: window_len=5, match_len=5, line_score=0.200, ratio_lines=0.200, final_score=0.340
trace:         score_window: window_len=9, match_len=5, line_score=0.576, ratio_lines=0.429, final_score=0.576
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.314
trace:         score_window: window_len=10, match_len=5, line_score=0.570, ratio_lines=0.400, final_score=0.570
trace:         score_window: window_len=11, match_len=5, line_score=0.564, ratio_lines=0.375, final_score=0.564
trace:         score_window: window_len=6, match_len=5, line_score=0.198, ratio_lines=0.182, final_score=0.274
trace:         score_window: window_len=3, match_len=5, line_score=0.250, ratio_lines=0.250, final_score=0.325
trace:         score_window: window_len=12, match_len=5, line_score=0.558, ratio_lines=0.353, final_score=0.558
trace:         score_window: window_len=13, match_len=5, line_score=0.552, ratio_lines=0.333, final_score=0.552
trace:         score_window: window_len=7, match_len=5, line_score=0.196, ratio_lines=0.167, final_score=0.250
trace:         score_window: window_len=2, match_len=5, line_score=0.286, ratio_lines=0.286, final_score=0.319
trace:         score_window: window_len=14, match_len=5, line_score=0.546, ratio_lines=0.316, final_score=0.546
trace:         score_window: window_len=15, match_len=5, line_score=0.540, ratio_lines=0.300, final_score=0.540
trace:         score_window: window_len=8, match_len=5, line_score=0.194, ratio_lines=0.154, final_score=0.249
trace:         score_window: window_len=16, match_len=5, line_score=0.534, ratio_lines=0.286, final_score=0.534
trace:         score_window: window_len=9, match_len=5, line_score=0.192, ratio_lines=0.143, final_score=0.221
trace:         score_window: window_len=17, match_len=5, line_score=0.528, ratio_lines=0.273, final_score=0.528
trace:         score_window: window_len=18, match_len=5, line_score=0.522, ratio_lines=0.261, final_score=0.522
trace:         score_window: window_len=5, match_len=5, line_score=0.200, ratio_lines=0.200, final_score=0.276
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.244
trace:         score_window: window_len=19, match_len=5, line_score=0.516, ratio_lines=0.250, final_score=0.516
trace:         score_window: window_len=6, match_len=5, line_score=0.198, ratio_lines=0.182, final_score=0.252
trace:         score_window: window_len=20, match_len=5, line_score=0.510, ratio_lines=0.240, final_score=0.510
trace:         score_window: window_len=21, match_len=5, line_score=0.504, ratio_lines=0.231, final_score=0.504
trace:         score_window: window_len=7, match_len=5, line_score=0.196, ratio_lines=0.167, final_score=0.250
trace:         score_window: window_len=22, match_len=5, line_score=0.664, ratio_lines=0.296, final_score=0.664
trace:         score_window: window_len=8, match_len=5, line_score=0.194, ratio_lines=0.154, final_score=0.222
trace:         score_window: window_len=4, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.181
trace:         score_window: window_len=5, match_len=5, line_score=0.200, ratio_lines=0.200, final_score=0.255
trace:         score_window: window_len=6, match_len=5, line_score=0.198, ratio_lines=0.182, final_score=0.343
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.256
trace:         score_window: window_len=3, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.187
trace:         score_window: window_len=6, match_len=5, line_score=0.198, ratio_lines=0.182, final_score=0.277
trace:         score_window: window_len=7, match_len=5, line_score=0.392, ratio_lines=0.333, final_score=0.426
trace:         score_window: window_len=3, match_len=5, line_score=0.250, ratio_lines=0.250, final_score=0.290
trace:         score_window: window_len=8, match_len=5, line_score=0.582, ratio_lines=0.462, final_score=0.582
trace:         score_window: window_len=9, match_len=5, line_score=0.576, ratio_lines=0.429, final_score=0.576
trace:         score_window: window_len=10, match_len=5, line_score=0.570, ratio_lines=0.400, final_score=0.570
trace:         score_window: window_len=7, match_len=5, line_score=0.196, ratio_lines=0.167, final_score=0.198
trace:         score_window: window_len=11, match_len=5, line_score=0.564, ratio_lines=0.375, final_score=0.564
trace:         score_window: window_len=12, match_len=5, line_score=0.558, ratio_lines=0.353, final_score=0.558
trace:         score_window: window_len=8, match_len=5, line_score=0.194, ratio_lines=0.154, final_score=0.194
trace:         score_window: window_len=13, match_len=5, line_score=0.552, ratio_lines=0.333, final_score=0.552
trace:         score_window: window_len=14, match_len=5, line_score=0.546, ratio_lines=0.316, final_score=0.546
trace:         score_window: window_len=9, match_len=5, line_score=0.192, ratio_lines=0.143, final_score=0.195
trace:         score_window: window_len=15, match_len=5, line_score=0.540, ratio_lines=0.300, final_score=0.540
trace:         score_window: window_len=16, match_len=5, line_score=0.534, ratio_lines=0.286, final_score=0.534
trace:         score_window: window_len=10, match_len=5, line_score=0.190, ratio_lines=0.133, final_score=0.193
trace:         score_window: window_len=17, match_len=5, line_score=0.528, ratio_lines=0.273, final_score=0.528
trace:         score_window: window_len=5, match_len=5, line_score=0.200, ratio_lines=0.200, final_score=0.265
trace:         score_window: window_len=18, match_len=5, line_score=0.522, ratio_lines=0.261, final_score=0.522
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.242
trace:         score_window: window_len=19, match_len=5, line_score=0.516, ratio_lines=0.250, final_score=0.516
trace:         score_window: window_len=6, match_len=5, line_score=0.198, ratio_lines=0.182, final_score=0.198
trace:         score_window: window_len=3, match_len=5, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=20, match_len=5, line_score=0.510, ratio_lines=0.240, final_score=0.510
trace:         score_window: window_len=21, match_len=5, line_score=0.672, ratio_lines=0.308, final_score=0.672
trace:         score_window: window_len=7, match_len=5, line_score=0.196, ratio_lines=0.167, final_score=0.196
trace:         score_window: window_len=2, match_len=5, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=5, match_len=5, line_score=0.200, ratio_lines=0.200, final_score=0.340
trace:         score_window: window_len=8, match_len=5, line_score=0.194, ratio_lines=0.154, final_score=0.195
trace:         score_window: window_len=4, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.241
trace:         score_window: window_len=6, match_len=5, line_score=0.396, ratio_lines=0.364, final_score=0.468
trace:         score_window: window_len=3, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.207
trace:         score_window: window_len=9, match_len=5, line_score=0.192, ratio_lines=0.143, final_score=0.196
trace:         score_window: window_len=7, match_len=5, line_score=0.588, ratio_lines=0.500, final_score=0.588
trace:         score_window: window_len=2, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.181
trace:         score_window: window_len=8, match_len=5, line_score=0.582, ratio_lines=0.462, final_score=0.582
trace:         score_window: window_len=5, match_len=5, line_score=0.200, ratio_lines=0.200, final_score=0.235
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.347
trace:         score_window: window_len=9, match_len=5, line_score=0.576, ratio_lines=0.429, final_score=0.576
trace:         score_window: window_len=10, match_len=5, line_score=0.570, ratio_lines=0.400, final_score=0.570
trace:         score_window: window_len=6, match_len=5, line_score=0.198, ratio_lines=0.182, final_score=0.218
trace:         score_window: window_len=11, match_len=5, line_score=0.564, ratio_lines=0.375, final_score=0.564
trace:         score_window: window_len=3, match_len=5, line_score=0.250, ratio_lines=0.250, final_score=0.322
trace:         score_window: window_len=12, match_len=5, line_score=0.558, ratio_lines=0.353, final_score=0.558
trace:         score_window: window_len=7, match_len=5, line_score=0.196, ratio_lines=0.167, final_score=0.220
trace:         score_window: window_len=13, match_len=5, line_score=0.552, ratio_lines=0.333, final_score=0.552
trace:         score_window: window_len=2, match_len=5, line_score=0.286, ratio_lines=0.286, final_score=0.336
trace:         score_window: window_len=14, match_len=5, line_score=0.546, ratio_lines=0.316, final_score=0.546
trace:         score_window: window_len=8, match_len=5, line_score=0.194, ratio_lines=0.154, final_score=0.215
trace:         score_window: window_len=15, match_len=5, line_score=0.540, ratio_lines=0.300, final_score=0.540
trace:         score_window: window_len=16, match_len=5, line_score=0.534, ratio_lines=0.286, final_score=0.534
trace:         score_window: window_len=9, match_len=5, line_score=0.192, ratio_lines=0.143, final_score=0.192
trace:         score_window: window_len=17, match_len=5, line_score=0.528, ratio_lines=0.273, final_score=0.528
trace:         score_window: window_len=5, match_len=5, line_score=0.200, ratio_lines=0.200, final_score=0.220
trace:         score_window: window_len=18, match_len=5, line_score=0.522, ratio_lines=0.261, final_score=0.522
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.222
trace:         score_window: window_len=19, match_len=5, line_score=0.516, ratio_lines=0.250, final_score=0.516
trace:         score_window: window_len=20, match_len=5, line_score=0.680, ratio_lines=0.320, final_score=0.680
trace:         score_window: window_len=6, match_len=5, line_score=0.198, ratio_lines=0.182, final_score=0.220
trace:         score_window: window_len=3, match_len=5, line_score=0.250, ratio_lines=0.250, final_score=0.315
trace:         score_window: window_len=5, match_len=5, line_score=0.400, ratio_lines=0.400, final_score=0.520
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.336
trace:         score_window: window_len=6, match_len=5, line_score=0.594, ratio_lines=0.545, final_score=0.618
trace:         score_window: window_len=7, match_len=5, line_score=0.196, ratio_lines=0.167, final_score=0.217
trace:         score_window: window_len=3, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.224
trace:         score_window: window_len=7, match_len=5, line_score=0.588, ratio_lines=0.500, final_score=0.629
trace:         score_window: window_len=8, match_len=5, line_score=0.194, ratio_lines=0.154, final_score=0.194
trace:         score_window: window_len=2, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.136
trace:         score_window: window_len=8, match_len=5, line_score=0.582, ratio_lines=0.462, final_score=0.582
trace:         score_window: window_len=5, match_len=5, line_score=0.200, ratio_lines=0.200, final_score=0.260
trace:         score_window: window_len=9, match_len=5, line_score=0.576, ratio_lines=0.429, final_score=0.576
trace:         score_window: window_len=10, match_len=5, line_score=0.570, ratio_lines=0.400, final_score=0.570
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.261
trace:         score_window: window_len=11, match_len=5, line_score=0.564, ratio_lines=0.375, final_score=0.564
trace:         score_window: window_len=12, match_len=5, line_score=0.558, ratio_lines=0.353, final_score=0.558
trace:         score_window: window_len=6, match_len=5, line_score=0.198, ratio_lines=0.182, final_score=0.255
trace:         score_window: window_len=3, match_len=5, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=13, match_len=5, line_score=0.552, ratio_lines=0.333, final_score=0.552
trace:         score_window: window_len=14, match_len=5, line_score=0.546, ratio_lines=0.316, final_score=0.546
trace:         score_window: window_len=7, match_len=5, line_score=0.196, ratio_lines=0.167, final_score=0.212
trace:         score_window: window_len=2, match_len=5, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=15, match_len=5, line_score=0.540, ratio_lines=0.300, final_score=0.540
trace:         score_window: window_len=5, match_len=5, line_score=0.200, ratio_lines=0.200, final_score=0.284
trace:         score_window: window_len=16, match_len=5, line_score=0.534, ratio_lines=0.286, final_score=0.534
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.288
trace:         score_window: window_len=17, match_len=5, line_score=0.528, ratio_lines=0.273, final_score=0.528
trace:         score_window: window_len=6, match_len=5, line_score=0.198, ratio_lines=0.182, final_score=0.230
trace:         score_window: window_len=18, match_len=5, line_score=0.522, ratio_lines=0.261, final_score=0.522
trace:         score_window: window_len=3, match_len=5, line_score=0.250, ratio_lines=0.250, final_score=0.291
trace:         score_window: window_len=19, match_len=5, line_score=0.688, ratio_lines=0.333, final_score=0.688
trace:         score_window: window_len=5, match_len=5, line_score=0.600, ratio_lines=0.600, final_score=0.722
trace:         score_window: window_len=7, match_len=5, line_score=0.196, ratio_lines=0.167, final_score=0.232
trace:         score_window: window_len=4, match_len=5, line_score=0.444, ratio_lines=0.444, final_score=0.746
trace:         score_window: window_len=2, match_len=5, line_score=0.286, ratio_lines=0.286, final_score=0.319
trace:         score_window: window_len=6, match_len=5, line_score=0.594, ratio_lines=0.545, final_score=0.732
trace:         score_window: window_len=3, match_len=5, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=7, match_len=5, line_score=0.588, ratio_lines=0.500, final_score=0.588
trace:         score_window: window_len=8, match_len=5, line_score=0.582, ratio_lines=0.462, final_score=0.582
trace:         score_window: window_len=5, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.200
trace:         score_window: window_len=9, match_len=5, line_score=0.576, ratio_lines=0.429, final_score=0.576
trace:         score_window: window_len=4, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.262
trace:         score_window: window_len=10, match_len=5, line_score=0.570, ratio_lines=0.400, final_score=0.570
trace:         score_window: window_len=11, match_len=5, line_score=0.564, ratio_lines=0.375, final_score=0.564
trace:         score_window: window_len=12, match_len=5, line_score=0.558, ratio_lines=0.353, final_score=0.558
trace:         score_window: window_len=6, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.216
trace:         score_window: window_len=13, match_len=5, line_score=0.552, ratio_lines=0.333, final_score=0.552
trace:         score_window: window_len=3, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.266
trace:         score_window: window_len=14, match_len=5, line_score=0.546, ratio_lines=0.316, final_score=0.546
trace:         score_window: window_len=2, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.266
trace:         score_window: window_len=15, match_len=5, line_score=0.540, ratio_lines=0.300, final_score=0.540
trace:         score_window: window_len=16, match_len=5, line_score=0.534, ratio_lines=0.286, final_score=0.534
trace:         score_window: window_len=5, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.131
trace:         score_window: window_len=17, match_len=5, line_score=0.528, ratio_lines=0.273, final_score=0.528
trace:         score_window: window_len=4, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.220
trace:         score_window: window_len=18, match_len=5, line_score=0.696, ratio_lines=0.348, final_score=0.696
trace:         score_window: window_len=5, match_len=5, line_score=0.600, ratio_lines=0.600, final_score=0.740
trace:         score_window: window_len=4, match_len=5, line_score=0.667, ratio_lines=0.667, final_score=0.731
trace:         score_window: window_len=6, match_len=5, line_score=0.594, ratio_lines=0.545, final_score=0.730
trace:         score_window: window_len=3, match_len=5, line_score=0.500, ratio_lines=0.500, final_score=0.901
trace:         score_window: window_len=7, match_len=5, line_score=0.588, ratio_lines=0.500, final_score=0.588
trace:         score_window: window_len=2, match_len=5, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=8, match_len=5, line_score=0.582, ratio_lines=0.462, final_score=0.582
trace:         score_window: window_len=9, match_len=5, line_score=0.576, ratio_lines=0.429, final_score=0.576
trace:         score_window: window_len=10, match_len=5, line_score=0.570, ratio_lines=0.400, final_score=0.570
trace:         score_window: window_len=11, match_len=5, line_score=0.564, ratio_lines=0.375, final_score=0.564
trace:         score_window: window_len=12, match_len=5, line_score=0.558, ratio_lines=0.353, final_score=0.558
trace:         score_window: window_len=13, match_len=5, line_score=0.552, ratio_lines=0.333, final_score=0.552
trace:         score_window: window_len=5, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.149
trace:         score_window: window_len=14, match_len=5, line_score=0.546, ratio_lines=0.316, final_score=0.546
trace:         score_window: window_len=4, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.157
trace:         score_window: window_len=15, match_len=5, line_score=0.540, ratio_lines=0.300, final_score=0.540
trace:         score_window: window_len=16, match_len=5, line_score=0.534, ratio_lines=0.286, final_score=0.534
trace:         score_window: window_len=4, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.155
trace:         score_window: window_len=5, match_len=5, line_score=0.600, ratio_lines=0.600, final_score=0.741
trace:         score_window: window_len=4, match_len=5, line_score=0.667, ratio_lines=0.667, final_score=0.828
trace:         score_window: window_len=6, match_len=5, line_score=0.594, ratio_lines=0.545, final_score=0.594
trace:         score_window: window_len=7, match_len=5, line_score=0.588, ratio_lines=0.500, final_score=0.588
trace:         score_window: window_len=3, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.165
trace:         score_window: window_len=2, match_len=5, line_score=0.571, ratio_lines=0.571, final_score=0.710
trace:         score_window: window_len=8, match_len=5, line_score=0.582, ratio_lines=0.462, final_score=0.582
trace:         score_window: window_len=9, match_len=5, line_score=0.576, ratio_lines=0.429, final_score=0.576
trace:         score_window: window_len=10, match_len=5, line_score=0.570, ratio_lines=0.400, final_score=0.570
trace:         score_window: window_len=11, match_len=5, line_score=0.564, ratio_lines=0.375, final_score=0.564
trace:         score_window: window_len=3, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.156
trace:         score_window: window_len=12, match_len=5, line_score=0.558, ratio_lines=0.353, final_score=0.558
trace:         score_window: window_len=13, match_len=5, line_score=0.552, ratio_lines=0.333, final_score=0.552
trace:         score_window: window_len=2, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.167
trace:         score_window: window_len=14, match_len=5, line_score=0.546, ratio_lines=0.316, final_score=0.546
trace:         score_window: window_len=15, match_len=5, line_score=0.540, ratio_lines=0.300, final_score=0.540
trace:         score_window: window_len=2, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.174
trace:         score_window: window_len=5, match_len=5, line_score=0.400, ratio_lines=0.400, final_score=0.400
trace:         score_window: window_len=4, match_len=5, line_score=0.444, ratio_lines=0.444, final_score=0.726
trace:         score_window: window_len=6, match_len=5, line_score=0.396, ratio_lines=0.364, final_score=0.396
trace:         score_window: window_len=2, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.209
trace:         score_window: window_len=3, match_len=5, line_score=0.500, ratio_lines=0.500, final_score=0.750
trace:         score_window: window_len=7, match_len=5, line_score=0.392, ratio_lines=0.333, final_score=0.392
trace:         score_window: window_len=2, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.143
trace:         score_window: window_len=2, match_len=5, line_score=0.571, ratio_lines=0.571, final_score=0.742
trace:         score_window: window_len=8, match_len=5, line_score=0.388, ratio_lines=0.308, final_score=0.388
trace:         score_window: window_len=5, match_len=5, line_score=0.200, ratio_lines=0.200, final_score=0.239
trace:         score_window: window_len=9, match_len=5, line_score=0.384, ratio_lines=0.286, final_score=0.384
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.280
trace:         score_window: window_len=10, match_len=5, line_score=0.380, ratio_lines=0.267, final_score=0.380
trace:         score_window: window_len=11, match_len=5, line_score=0.376, ratio_lines=0.250, final_score=0.376
trace:         score_window: window_len=6, match_len=5, line_score=0.198, ratio_lines=0.182, final_score=0.226
trace:         score_window: window_len=12, match_len=5, line_score=0.372, ratio_lines=0.235, final_score=0.372
trace:         score_window: window_len=3, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.187
trace:         score_window: window_len=2, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.200
trace:         score_window: window_len=13, match_len=5, line_score=0.368, ratio_lines=0.222, final_score=0.368
trace:         score_window: window_len=14, match_len=5, line_score=0.364, ratio_lines=0.211, final_score=0.364
trace:         score_window: window_len=9, match_len=5, line_score=0.384, ratio_lines=0.286, final_score=0.384
trace:         score_window: window_len=15, match_len=5, line_score=0.540, ratio_lines=0.300, final_score=0.540
trace:         score_window: window_len=10, match_len=5, line_score=0.570, ratio_lines=0.400, final_score=0.570
trace:         score_window: window_len=18, match_len=5, line_score=0.696, ratio_lines=0.348, final_score=0.696
trace:         score_window: window_len=19, match_len=5, line_score=0.688, ratio_lines=0.333, final_score=0.688
trace:         score_window: window_len=18, match_len=5, line_score=0.696, ratio_lines=0.348, final_score=0.696
trace:         score_window: window_len=20, match_len=5, line_score=0.680, ratio_lines=0.320, final_score=0.680
trace:         score_window: window_len=19, match_len=5, line_score=0.688, ratio_lines=0.333, final_score=0.688
trace:         score_window: window_len=21, match_len=5, line_score=0.672, ratio_lines=0.308, final_score=0.672
trace:         score_window: window_len=20, match_len=5, line_score=0.680, ratio_lines=0.320, final_score=0.680
trace:         score_window: window_len=22, match_len=5, line_score=0.664, ratio_lines=0.296, final_score=0.664
trace:         score_window: window_len=21, match_len=5, line_score=0.672, ratio_lines=0.308, final_score=0.672
trace:         score_window: window_len=23, match_len=5, line_score=0.656, ratio_lines=0.286, final_score=0.656
trace:         score_window: window_len=24, match_len=5, line_score=0.648, ratio_lines=0.276, final_score=0.648
trace:         score_window: window_len=22, match_len=5, line_score=0.664, ratio_lines=0.296, final_score=0.664
trace:         score_window: window_len=25, match_len=5, line_score=0.640, ratio_lines=0.267, final_score=0.640
trace:         score_window: window_len=23, match_len=5, line_score=0.656, ratio_lines=0.286, final_score=0.656
trace:         score_window: window_len=26, match_len=5, line_score=0.632, ratio_lines=0.258, final_score=0.632
trace:         score_window: window_len=24, match_len=5, line_score=0.648, ratio_lines=0.276, final_score=0.648
trace:         score_window: window_len=27, match_len=5, line_score=0.624, ratio_lines=0.250, final_score=0.624
trace:         score_window: window_len=5, match_len=5, line_score=0.200, ratio_lines=0.200, final_score=0.200
trace:         score_window: window_len=25, match_len=5, line_score=0.640, ratio_lines=0.267, final_score=0.640
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.222
trace:         score_window: window_len=3, match_len=5, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=26, match_len=5, line_score=0.632, ratio_lines=0.258, final_score=0.632
trace:         score_window: window_len=2, match_len=5, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=27, match_len=5, line_score=0.624, ratio_lines=0.250, final_score=0.624
trace:         score_window: window_len=14, match_len=5, line_score=0.546, ratio_lines=0.316, final_score=0.546
trace:         score_window: window_len=5, match_len=5, line_score=0.200, ratio_lines=0.200, final_score=0.213
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.222
trace:         score_window: window_len=18, match_len=5, line_score=0.696, ratio_lines=0.348, final_score=0.696
trace:         score_window: window_len=3, match_len=5, line_score=0.250, ratio_lines=0.250, final_score=0.266
trace:         score_window: window_len=2, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.163
trace:         score_window: window_len=19, match_len=5, line_score=0.688, ratio_lines=0.333, final_score=0.688
trace:         score_window: window_len=8, match_len=5, line_score=0.388, ratio_lines=0.308, final_score=0.388
trace:         score_window: window_len=20, match_len=5, line_score=0.680, ratio_lines=0.320, final_score=0.680
trace:         score_window: window_len=9, match_len=5, line_score=0.576, ratio_lines=0.429, final_score=0.576
trace:         score_window: window_len=21, match_len=5, line_score=0.672, ratio_lines=0.308, final_score=0.672
trace:         score_window: window_len=18, match_len=5, line_score=0.696, ratio_lines=0.348, final_score=0.696
trace:         score_window: window_len=19, match_len=5, line_score=0.688, ratio_lines=0.333, final_score=0.688
trace:         score_window: window_len=22, match_len=5, line_score=0.664, ratio_lines=0.296, final_score=0.664
trace:         score_window: window_len=20, match_len=5, line_score=0.680, ratio_lines=0.320, final_score=0.680
trace:         score_window: window_len=23, match_len=5, line_score=0.656, ratio_lines=0.286, final_score=0.656
trace:         score_window: window_len=21, match_len=5, line_score=0.672, ratio_lines=0.308, final_score=0.672
trace:         score_window: window_len=24, match_len=5, line_score=0.648, ratio_lines=0.276, final_score=0.648
trace:         score_window: window_len=22, match_len=5, line_score=0.664, ratio_lines=0.296, final_score=0.664
trace:         score_window: window_len=23, match_len=5, line_score=0.656, ratio_lines=0.286, final_score=0.656
trace:         score_window: window_len=25, match_len=5, line_score=0.640, ratio_lines=0.267, final_score=0.640
trace:         score_window: window_len=24, match_len=5, line_score=0.648, ratio_lines=0.276, final_score=0.648
trace:         score_window: window_len=26, match_len=5, line_score=0.632, ratio_lines=0.258, final_score=0.632
trace:         score_window: window_len=25, match_len=5, line_score=0.640, ratio_lines=0.267, final_score=0.640
trace:         score_window: window_len=27, match_len=5, line_score=0.624, ratio_lines=0.250, final_score=0.624
trace:         score_window: window_len=26, match_len=5, line_score=0.632, ratio_lines=0.258, final_score=0.632
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.230
trace:         score_window: window_len=27, match_len=5, line_score=0.624, ratio_lines=0.250, final_score=0.624
trace:         score_window: window_len=3, match_len=5, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=5, match_len=5, line_score=0.200, ratio_lines=0.200, final_score=0.225
trace:         score_window: window_len=2, match_len=5, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.256
trace:         score_window: window_len=12, match_len=5, line_score=0.372, ratio_lines=0.235, final_score=0.372
trace:         score_window: window_len=6, match_len=5, line_score=0.198, ratio_lines=0.182, final_score=0.233
trace:         score_window: window_len=3, match_len=5, line_score=0.250, ratio_lines=0.250, final_score=0.282
trace:         score_window: window_len=13, match_len=5, line_score=0.552, ratio_lines=0.333, final_score=0.552
trace:         score_window: window_len=7, match_len=5, line_score=0.392, ratio_lines=0.333, final_score=0.392
trace:         score_window: window_len=2, match_len=5, line_score=0.286, ratio_lines=0.286, final_score=0.345
trace:         score_window: window_len=18, match_len=5, line_score=0.696, ratio_lines=0.348, final_score=0.696
trace:         score_window: window_len=8, match_len=5, line_score=0.582, ratio_lines=0.462, final_score=0.582
trace:         score_window: window_len=19, match_len=5, line_score=0.688, ratio_lines=0.333, final_score=0.688
trace:         score_window: window_len=18, match_len=5, line_score=0.696, ratio_lines=0.348, final_score=0.696
trace:         score_window: window_len=19, match_len=5, line_score=0.688, ratio_lines=0.333, final_score=0.688
trace:         score_window: window_len=20, match_len=5, line_score=0.680, ratio_lines=0.320, final_score=0.680
trace:         score_window: window_len=20, match_len=5, line_score=0.680, ratio_lines=0.320, final_score=0.680
trace:         score_window: window_len=21, match_len=5, line_score=0.672, ratio_lines=0.308, final_score=0.672
trace:         score_window: window_len=21, match_len=5, line_score=0.672, ratio_lines=0.308, final_score=0.672
trace:         score_window: window_len=22, match_len=5, line_score=0.664, ratio_lines=0.296, final_score=0.664
trace:         score_window: window_len=22, match_len=5, line_score=0.664, ratio_lines=0.296, final_score=0.664
trace:         score_window: window_len=23, match_len=5, line_score=0.656, ratio_lines=0.286, final_score=0.656
trace:         score_window: window_len=23, match_len=5, line_score=0.656, ratio_lines=0.286, final_score=0.656
trace:         score_window: window_len=24, match_len=5, line_score=0.648, ratio_lines=0.276, final_score=0.648
trace:         score_window: window_len=24, match_len=5, line_score=0.648, ratio_lines=0.276, final_score=0.648
trace:         score_window: window_len=25, match_len=5, line_score=0.640, ratio_lines=0.267, final_score=0.640
trace:         score_window: window_len=26, match_len=5, line_score=0.632, ratio_lines=0.258, final_score=0.632
trace:         score_window: window_len=25, match_len=5, line_score=0.640, ratio_lines=0.267, final_score=0.640
trace:         score_window: window_len=27, match_len=5, line_score=0.624, ratio_lines=0.250, final_score=0.624
trace:         score_window: window_len=26, match_len=5, line_score=0.632, ratio_lines=0.258, final_score=0.632
trace:         score_window: window_len=5, match_len=5, line_score=0.200, ratio_lines=0.200, final_score=0.239
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.249
trace:         score_window: window_len=27, match_len=5, line_score=0.624, ratio_lines=0.250, final_score=0.624
trace:         score_window: window_len=6, match_len=5, line_score=0.396, ratio_lines=0.364, final_score=0.396
trace:         score_window: window_len=3, match_len=5, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=3, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.179
trace:         score_window: window_len=7, match_len=5, line_score=0.588, ratio_lines=0.500, final_score=0.588
trace:         score_window: window_len=2, match_len=5, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=2, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.180
trace:         score_window: window_len=18, match_len=5, line_score=0.696, ratio_lines=0.348, final_score=0.696
trace:         score_window: window_len=11, match_len=5, line_score=0.376, ratio_lines=0.250, final_score=0.376
trace:         score_window: window_len=19, match_len=5, line_score=0.688, ratio_lines=0.333, final_score=0.688
trace:         score_window: window_len=20, match_len=5, line_score=0.680, ratio_lines=0.320, final_score=0.680
trace:         score_window: window_len=12, match_len=5, line_score=0.558, ratio_lines=0.353, final_score=0.558
trace:         score_window: window_len=21, match_len=5, line_score=0.672, ratio_lines=0.308, final_score=0.672
trace:         score_window: window_len=22, match_len=5, line_score=0.664, ratio_lines=0.296, final_score=0.664
trace:         score_window: window_len=18, match_len=5, line_score=0.696, ratio_lines=0.348, final_score=0.696
trace:         score_window: window_len=23, match_len=5, line_score=0.656, ratio_lines=0.286, final_score=0.656
trace:         score_window: window_len=19, match_len=5, line_score=0.688, ratio_lines=0.333, final_score=0.688
trace:         score_window: window_len=24, match_len=5, line_score=0.648, ratio_lines=0.276, final_score=0.648
trace:         score_window: window_len=25, match_len=5, line_score=0.640, ratio_lines=0.267, final_score=0.640
trace:         score_window: window_len=20, match_len=5, line_score=0.680, ratio_lines=0.320, final_score=0.680
trace:         score_window: window_len=26, match_len=5, line_score=0.632, ratio_lines=0.258, final_score=0.632
trace:         score_window: window_len=21, match_len=5, line_score=0.672, ratio_lines=0.308, final_score=0.672
trace:         score_window: window_len=27, match_len=5, line_score=0.624, ratio_lines=0.250, final_score=0.624
trace:         score_window: window_len=5, match_len=5, line_score=0.200, ratio_lines=0.200, final_score=0.269
trace:         score_window: window_len=22, match_len=5, line_score=0.664, ratio_lines=0.296, final_score=0.664
trace:         score_window: window_len=4, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.219
trace:         score_window: window_len=23, match_len=5, line_score=0.656, ratio_lines=0.286, final_score=0.656
trace:         score_window: window_len=6, match_len=5, line_score=0.396, ratio_lines=0.364, final_score=0.396
trace:         score_window: window_len=3, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.226
trace:         score_window: window_len=24, match_len=5, line_score=0.648, ratio_lines=0.276, final_score=0.648
trace:         score_window: window_len=7, match_len=5, line_score=0.588, ratio_lines=0.500, final_score=0.588
trace:         score_window: window_len=8, match_len=5, line_score=0.582, ratio_lines=0.462, final_score=0.582
trace:         score_window: window_len=25, match_len=5, line_score=0.640, ratio_lines=0.267, final_score=0.640
trace:         score_window: window_len=9, match_len=5, line_score=0.576, ratio_lines=0.429, final_score=0.576
trace:         score_window: window_len=26, match_len=5, line_score=0.632, ratio_lines=0.258, final_score=0.632
trace:         score_window: window_len=10, match_len=5, line_score=0.570, ratio_lines=0.400, final_score=0.570
trace:         score_window: window_len=27, match_len=5, line_score=0.624, ratio_lines=0.250, final_score=0.624
trace:         score_window: window_len=11, match_len=5, line_score=0.564, ratio_lines=0.375, final_score=0.564
trace:         score_window: window_len=3, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.147
trace:         score_window: window_len=12, match_len=5, line_score=0.558, ratio_lines=0.353, final_score=0.558
trace:         score_window: window_len=10, match_len=5, line_score=0.380, ratio_lines=0.267, final_score=0.380
trace:         score_window: window_len=13, match_len=5, line_score=0.552, ratio_lines=0.333, final_score=0.552
trace:         score_window: window_len=14, match_len=5, line_score=0.546, ratio_lines=0.316, final_score=0.546
trace:         score_window: window_len=11, match_len=5, line_score=0.564, ratio_lines=0.375, final_score=0.564
trace:         score_window: window_len=15, match_len=5, line_score=0.540, ratio_lines=0.300, final_score=0.540
trace:         score_window: window_len=16, match_len=5, line_score=0.534, ratio_lines=0.286, final_score=0.534
trace:         score_window: window_len=18, match_len=5, line_score=0.696, ratio_lines=0.348, final_score=0.696
trace:         score_window: window_len=17, match_len=5, line_score=0.528, ratio_lines=0.273, final_score=0.528
trace:         score_window: window_len=19, match_len=5, line_score=0.688, ratio_lines=0.333, final_score=0.688
trace:         score_window: window_len=18, match_len=5, line_score=0.522, ratio_lines=0.261, final_score=0.522
trace:         score_window: window_len=19, match_len=5, line_score=0.516, ratio_lines=0.250, final_score=0.516
trace:         score_window: window_len=20, match_len=5, line_score=0.680, ratio_lines=0.320, final_score=0.680
trace:         score_window: window_len=20, match_len=5, line_score=0.510, ratio_lines=0.240, final_score=0.510
trace:         score_window: window_len=21, match_len=5, line_score=0.672, ratio_lines=0.308, final_score=0.672
trace:         score_window: window_len=21, match_len=5, line_score=0.504, ratio_lines=0.231, final_score=0.504
trace:         score_window: window_len=22, match_len=5, line_score=0.664, ratio_lines=0.296, final_score=0.664
trace:         score_window: window_len=22, match_len=5, line_score=0.498, ratio_lines=0.222, final_score=0.498
trace:         score_window: window_len=23, match_len=5, line_score=0.492, ratio_lines=0.214, final_score=0.492
trace:         score_window: window_len=23, match_len=5, line_score=0.656, ratio_lines=0.286, final_score=0.656
trace:         score_window: window_len=24, match_len=5, line_score=0.648, ratio_lines=0.276, final_score=0.648
trace:         score_window: window_len=5, match_len=5, line_score=0.400, ratio_lines=0.400, final_score=0.400
trace:         score_window: window_len=4, match_len=5, line_score=0.222, ratio_lines=0.222, final_score=0.284
trace:         score_window: window_len=25, match_len=5, line_score=0.640, ratio_lines=0.267, final_score=0.640
trace:         score_window: window_len=6, match_len=5, line_score=0.594, ratio_lines=0.545, final_score=0.594
trace:         score_window: window_len=3, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.222
trace:         score_window: window_len=26, match_len=5, line_score=0.632, ratio_lines=0.258, final_score=0.632
trace:         score_window: window_len=7, match_len=5, line_score=0.588, ratio_lines=0.500, final_score=0.588
trace:         score_window: window_len=2, match_len=5, line_score=0.000, ratio_lines=0.000, final_score=0.230
trace:         score_window: window_len=27, match_len=5, line_score=0.624, ratio_lines=0.250, final_score=0.624
trace:         score_window: window_len=5, match_len=5, line_score=0.600, ratio_lines=0.600, final_score=0.600
trace:         score_window: window_len=8, match_len=5, line_score=0.582, ratio_lines=0.462, final_score=0.582
trace:         score_window: window_len=4, match_len=5, line_score=0.444, ratio_lines=0.444, final_score=0.444
trace:         score_window: window_len=6, match_len=5, line_score=0.594, ratio_lines=0.545, final_score=0.594
trace:         score_window: window_len=3, match_len=5, line_score=0.250, ratio_lines=0.250, final_score=0.250
trace:         score_window: window_len=9, match_len=5, line_score=0.576, ratio_lines=0.429, final_score=0.576
trace:         score_window: window_len=7, match_len=5, line_score=0.588, ratio_lines=0.500, final_score=0.588
trace:         score_window: window_len=10, match_len=5, line_score=0.570, ratio_lines=0.400, final_score=0.570
trace:         score_window: window_len=8, match_len=5, line_score=0.582, ratio_lines=0.462, final_score=0.582
trace:         score_window: window_len=11, match_len=5, line_score=0.564, ratio_lines=0.375, final_score=0.564
trace:         score_window: window_len=9, match_len=5, line_score=0.576, ratio_lines=0.429, final_score=0.576
trace:         score_window: window_len=12, match_len=5, line_score=0.558, ratio_lines=0.353, final_score=0.558
trace:         score_window: window_len=13, match_len=5, line_score=0.552, ratio_lines=0.333, final_score=0.552
trace:         score_window: window_len=10, match_len=5, line_score=0.570, ratio_lines=0.400, final_score=0.570
trace:         score_window: window_len=11, match_len=5, line_score=0.564, ratio_lines=0.375, final_score=0.564
trace:         score_window: window_len=14, match_len=5, line_score=0.546, ratio_lines=0.316, final_score=0.546
trace:         score_window: window_len=12, match_len=5, line_score=0.558, ratio_lines=0.353, final_score=0.558
trace:         score_window: window_len=15, match_len=5, line_score=0.540, ratio_lines=0.300, final_score=0.540
trace:         score_window: window_len=13, match_len=5, line_score=0.552, ratio_lines=0.333, final_score=0.552
trace:         score_window: window_len=14, match_len=5, line_score=0.546, ratio_lines=0.316, final_score=0.546
trace:         score_window: window_len=16, match_len=5, line_score=0.534, ratio_lines=0.286, final_score=0.534
trace:         score_window: window_len=15, match_len=5, line_score=0.540, ratio_lines=0.300, final_score=0.540
trace:         score_window: window_len=17, match_len=5, line_score=0.528, ratio_lines=0.273, final_score=0.528
trace:         score_window: window_len=16, match_len=5, line_score=0.534, ratio_lines=0.286, final_score=0.534
trace:         score_window: window_len=18, match_len=5, line_score=0.522, ratio_lines=0.261, final_score=0.522
trace:         score_window: window_len=17, match_len=5, line_score=0.528, ratio_lines=0.273, final_score=0.528
trace:         score_window: window_len=18, match_len=5, line_score=0.522, ratio_lines=0.261, final_score=0.522
trace:         score_window: window_len=19, match_len=5, line_score=0.516, ratio_lines=0.250, final_score=0.516
trace:         score_window: window_len=19, match_len=5, line_score=0.516, ratio_lines=0.250, final_score=0.516
trace:         score_window: window_len=20, match_len=5, line_score=0.510, ratio_lines=0.240, final_score=0.510
trace:         score_window: window_len=20, match_len=5, line_score=0.510, ratio_lines=0.240, final_score=0.510
trace:         score_window: window_len=21, match_len=5, line_score=0.504, ratio_lines=0.231, final_score=0.504
trace:         score_window: window_len=21, match_len=5, line_score=0.504, ratio_lines=0.231, final_score=0.504
trace:         score_window: window_len=22, match_len=5, line_score=0.498, ratio_lines=0.222, final_score=0.498
trace:         score_window: window_len=22, match_len=5, line_score=0.498, ratio_lines=0.222, final_score=0.498
trace:         score_window: window_len=23, match_len=5, line_score=0.492, ratio_lines=0.214, final_score=0.492
trace:         score_window: window_len=23, match_len=5, line_score=0.492, ratio_lines=0.214, final_score=0.492
debug:       compute_scored_windows (parallel) complete: scored 1131 window(s). Best candidate score=0.901 at line 4645 (len=3).
trace:       Top fuzzy match candidates:
trace:         - Index 4644, Len 3: Score 0.901 (Ratio 0.901) | Content: ["            }\"", "", "            compile_check_conftest \"$CODE\" \"NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE\" \"\" \"functions\""]
trace:         - Index 4645, Len 17: Score 0.880 (Ratio 0.880) | Content: ["", "            compile_check_conftest \"$CODE\" \"NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE\" \"\" \"functions\"", "        ;;", "", "        # When adding a new conftest entry, please use the correct format for", "        # specifying the relevant upstream Linux kernel commit.", "        #", "        # <function> was added|removed|etc by commit <sha> (\"<commit message\")", "        # in <kernel-version> (<commit date>).", "", "        *)", "            # Unknown test name given", "            echo \"Error: unknown conftest '$1' requested\" >&2", "            exit 1", "        ;;", "    esac", "}"]
trace:         - Index 4644, Len 18: Score 0.870 (Ratio 0.870) | Content: ["            }\"", "", "            compile_check_conftest \"$CODE\" \"NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE\" \"\" \"functions\"", "        ;;", "", "        # When adding a new conftest entry, please use the correct format for", "        # specifying the relevant upstream Linux kernel commit.", "        #", "        # <function> was added|removed|etc by commit <sha> (\"<commit message\")", "        # in <kernel-version> (<commit date>).", "", "        *)", "            # Unknown test name given", "            echo \"Error: unknown conftest '$1' requested\" >&2", "            exit 1", "        ;;", "    esac", "}"]
trace:         - Index 4645, Len 18: Score 0.870 (Ratio 0.870) | Content: ["", "            compile_check_conftest \"$CODE\" \"NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE\" \"\" \"functions\"", "        ;;", "", "        # When adding a new conftest entry, please use the correct format for", "        # specifying the relevant upstream Linux kernel commit.", "        #", "        # <function> was added|removed|etc by commit <sha> (\"<commit message\")", "        # in <kernel-version> (<commit date>).", "", "        *)", "            # Unknown test name given", "            echo \"Error: unknown conftest '$1' requested\" >&2", "            exit 1", "        ;;", "    esac", "}", ""]
trace:         - Index 4643, Len 19: Score 0.860 (Ratio 0.860) | Content: ["                acpi_video_backlight_use_native(0);", "            }\"", "", "            compile_check_conftest \"$CODE\" \"NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE\" \"\" \"functions\"", "        ;;", "", "        # When adding a new conftest entry, please use the correct format for", "        # specifying the relevant upstream Linux kernel commit.", "        #", "        # <function> was added|removed|etc by commit <sha> (\"<commit message\")", "        # in <kernel-version> (<commit date>).", "", "        *)", "            # Unknown test name given", "            echo \"Error: unknown conftest '$1' requested\" >&2", "            exit 1", "        ;;", "    esac", "}"]
trace:         New best score: 0.490 (ratio 0.490 [l:0.000,w:0.000]) at index 4630 (window len 5)
trace:         New best score: 0.503 (ratio 0.503 [l:0.000,w:0.000]) at index 4630 (window len 4)
trace:         New best score: 0.612 (ratio 0.612 [l:0.000,w:0.000]) at index 4630 (window len 3)
trace:         New best score: 0.672 (ratio 0.672 [l:0.182,w:0.000]) at index 4630 (window len 17)
trace:         New best score: 0.697 (ratio 0.697 [l:0.207,w:0.000]) at index 4630 (window len 24)
trace:         Tie in score (0.697) and ratio (0.697). Adding candidate: index 4631, len 24
trace:         Tie in score (0.697) and ratio (0.697). Adding candidate: index 4632, len 24
trace:         Tie in score (0.697) and ratio (0.697). Adding candidate: index 4633, len 24
trace:         Tie in score (0.697) and ratio (0.697). Adding candidate: index 4634, len 24
trace:         Tie in score (0.697) and ratio (0.697). Adding candidate: index 4635, len 24
trace:         New best score: 0.780 (ratio 0.780 [l:0.312,w:0.780]) at index 4635 (window len 27)
trace:         New best score: 0.790 (ratio 0.790 [l:0.323,w:0.790]) at index 4636 (window len 26)
trace:         New best score: 0.800 (ratio 0.800 [l:0.333,w:0.800]) at index 4637 (window len 25)
trace:         New best score: 0.810 (ratio 0.810 [l:0.345,w:0.810]) at index 4638 (window len 24)
trace:         New best score: 0.820 (ratio 0.820 [l:0.357,w:0.820]) at index 4639 (window len 23)
trace:         New best score: 0.830 (ratio 0.830 [l:0.370,w:0.830]) at index 4640 (window len 22)
trace:         New best score: 0.840 (ratio 0.840 [l:0.385,w:0.840]) at index 4641 (window len 21)
trace:         New best score: 0.850 (ratio 0.850 [l:0.400,w:0.850]) at index 4642 (window len 20)
trace:         New best score: 0.860 (ratio 0.860 [l:0.417,w:0.860]) at index 4643 (window len 19)
trace:         New best score: 0.901 (ratio 0.901 [l:0.500,w:0.643]) at index 4644 (window len 3)
debug:     Strategy 3 (Fuzzy): 137 window(s) met threshold 0.70
trace:       Top 3 passing candidates: [("0.901", 4645, 3), ("0.880", 4646, 17), ("0.870", 4645, 18)]
debug:     Top fuzzy candidate: start line 4645 (len=3, score=0.901)
trace:       Adding candidate location at line 4646 (len=17, score=0.880)
trace:       Adding candidate location at line 4645 (len=18, score=0.870)
trace:       Adding candidate location at line 4646 (len=18, score=0.870)
trace:       Adding candidate location at line 4644 (len=19, score=0.860)
trace:       Adding candidate location at line 4645 (len=19, score=0.860)
trace:       Adding candidate location at line 4646 (len=19, score=0.860)
trace:       Adding candidate location at line 4643 (len=20, score=0.850)
trace:       Adding candidate location at line 4644 (len=20, score=0.850)
trace:       Adding candidate location at line 4645 (len=20, score=0.850)
trace:       Adding candidate location at line 4646 (len=20, score=0.850)
trace:       Adding candidate location at line 4642 (len=21, score=0.840)
trace:       Adding candidate location at line 4643 (len=21, score=0.840)
trace:       Adding candidate location at line 4644 (len=21, score=0.840)
trace:       Adding candidate location at line 4645 (len=21, score=0.840)
trace:       Adding candidate location at line 4646 (len=21, score=0.840)
trace:       Adding candidate location at line 4641 (len=22, score=0.830)
trace:       Adding candidate location at line 4642 (len=22, score=0.830)
trace:       Adding candidate location at line 4643 (len=22, score=0.830)
trace:       Adding candidate location at line 4644 (len=22, score=0.830)
trace:       Reached maximum candidate limit (20), stopping candidate collection
debug:     Strategy 3 (Fuzzy): selected 20 candidate location(s)
trace:   Pruned candidates by min_span 1: 20 -> 20 candidate(s)
trace: DefaultHunkFinder::find_candidate_locations: returning 20 candidate(s)
debug:   Found 20 candidate location(s) for hunk. Testing sequentially...
trace:   Evaluating candidate 1/20 at location HunkLocation { start_index: 4644, length: 3 } (match_type: Fuzzy { score: 0.9009090840816498 })
debug:   Found location HunkLocation { start_index: 4644, length: 3 } with match type Fuzzy { score: 0.9009090840816498 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 4645 (length 3), match_type=Fuzzy { score: 0.9009090840816498 }, total target lines=5090.
trace: Hunk::get_match_block: extracted 5 match line(s)
trace:     Match block lines: 5 | Total hunk lines: 17
trace:     Target slice to replace: ["            }\"", "", "            compile_check_conftest \"$CODE\" \"NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE\" \"\" \"functions\""]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=4644, len=3
trace:       File content in matched range (3 line(s)): ["            }\"", "", "            compile_check_conftest \"$CODE\" \"NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE\" \"\" \"functions\""]
trace:       Parsed hunk: 5 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 5 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.500
trace:       Initial Indentation Context: Hunk='            ', Target='            '
trace:       Active baseline indentation: hunk='            ', target='            '
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: '            }\"'
trace:       DiffOp::Equal: 2 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '            compile_check_conftest \"$CODE\" \"NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE\" \"\" \"functions\"'
trace:       DiffOp::Delete: 3 line(s) missing from target file (hunk old_idx=2)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 1/20 at HunkLocation { start_index: 4644, length: 3 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 2/20 at location HunkLocation { start_index: 4645, length: 17 } (match_type: Fuzzy { score: 0.8800000262260438 })
debug:   Found location HunkLocation { start_index: 4645, length: 17 } with match type Fuzzy { score: 0.8800000262260438 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 4646 (length 17), match_type=Fuzzy { score: 0.8800000262260438 }, total target lines=5090.
trace: Hunk::get_match_block: extracted 5 match line(s)
trace:     Match block lines: 5 | Total hunk lines: 17
trace:     Target slice to replace: ["", "            compile_check_conftest \"$CODE\" \"NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE\" \"\" \"functions\"", "        ;;", "", "        # When adding a new conftest entry, please use the correct format for", "        # specifying the relevant upstream Linux kernel commit.", "        #", "        # <function> was added|removed|etc by commit <sha> (\"<commit message\")", "        # in <kernel-version> (<commit date>).", "", "        *)", "            # Unknown test name given", "            echo \"Error: unknown conftest '$1' requested\" >&2", "            exit 1", "        ;;", "    esac", "}"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=4645, len=17
trace:       File content in matched range (17 line(s)): ["", "            compile_check_conftest \"$CODE\" \"NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE\" \"\" \"functions\"", "        ;;", "", "        # When adding a new conftest entry, please use the correct format for", "        # specifying the relevant upstream Linux kernel commit.", "        #", "        # <function> was added|removed|etc by commit <sha> (\"<commit message\")", "        # in <kernel-version> (<commit date>).", "", "        *)", "            # Unknown test name given", "            echo \"Error: unknown conftest '$1' requested\" >&2", "            exit 1", "        ;;", "    esac", "}"]
trace:       Parsed hunk: 5 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 5 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.455
trace:       Initial Indentation Context: Hunk='            ', Target='            '
trace:       Active baseline indentation: hunk='            ', target='            '
trace:       DiffOp::Equal: 3 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: ''
trace:         Equal: preserving target line: '            compile_check_conftest \"$CODE\" \"NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE\" \"\" \"functions\"'
trace:       Dynamic Indentation Update (Equal): Hunk='        ', Target='        '
trace:         Equal: preserving target line: '        ;;'
trace:         Appended 12 addition(s) after line 2
trace:         Equal: applying addition: ''
trace:         Equal: applying addition: '        # When adding a new conftest entry, please use the correct format for'
trace:         Equal: applying addition: '        # specifying the relevant upstream Linux kernel commit.'
trace:         Equal: applying addition: '        #'
trace:         Equal: applying addition: '        # <function> was added|removed|etc by commit <sha> (\"<commit message\")'
trace:         Equal: applying addition: '        # in <kernel-version> (<commit date>).'
trace:         Equal: applying addition: ''
trace:         Equal: applying addition: '        *)'
trace:         Equal: applying addition: '            # Unknown test name given'
trace:         Equal: applying addition: '            echo \"Error: unknown conftest \'$1\' requested\" >&2'
trace:         Equal: applying addition: '            exit 1'
trace:         Equal: applying addition: '        ;;'
trace:       DiffOp::Insert: preserving 12 local insertion line(s) from target file (new_idx=3)
trace:         Preserving inserted line: ''
trace:         Preserving inserted line: '        # When adding a new conftest entry, please use the correct format for'
trace:         Preserving inserted line: '        # specifying the relevant upstream Linux kernel commit.'
trace:         Preserving inserted line: '        #'
trace:         Preserving inserted line: '        # <function> was added|removed|etc by commit <sha> (\"<commit message\")'
trace:         Preserving inserted line: '        # in <kernel-version> (<commit date>).'
trace:         Preserving inserted line: ''
trace:         Preserving inserted line: '        *)'
trace:         Preserving inserted line: '            # Unknown test name given'
trace:         Preserving inserted line: '            echo \"Error: unknown conftest \'$1\' requested\" >&2'
trace:         Preserving inserted line: '            exit 1'
trace:         Preserving inserted line: '        ;;'
trace:       DiffOp::Equal: 2 line(s) aligned (hunk old_idx=3, file new_idx=15)
trace:       Dynamic Indentation Update (Equal): Hunk='    ', Target='    '
trace:         Equal: preserving target line: '    esac'
trace:         Equal: preserving target line: '}'
debug:     Robust reconstruction complete: produced 29 replacement line(s) for 17 target line(s).
trace:   Splicing final replacement block into target lines: range [4645..4662], replacement line count=29
  try_apply_hunk_at_location: successfully spliced hunk at line 4646 (replaced 17 line(s), resulting target lines=5102)
trace:     Replaced lines: ["", "            compile_check_conftest \"$CODE\" \"NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE\" \"\" \"functions\"", "        ;;", "", "        # When adding a new conftest entry, please use the correct format for", "        # specifying the relevant upstream Linux kernel commit.", "        #", "        # <function> was added|removed|etc by commit <sha> (\"<commit message\")", "        # in <kernel-version> (<commit date>).", "", "        *)", "            # Unknown test name given", "            echo \"Error: unknown conftest '$1' requested\" >&2", "            exit 1", "        ;;", "    esac", "}"]
debug:   Candidate 2/20 at HunkLocation { start_index: 4645, length: 17 } succeeded! Hunk applied cleanly.
debug:   HunkApplier: hunk 1 application outcome: Applied { location: HunkLocation { start_index: 4645, length: 17 }, match_type: Fuzzy { score: 0.8800000262260438 }, replaced_lines: ["", "            compile_check_conftest \"$CODE\" \"NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE\" \"\" \"functions\"", "        ;;", "", "        # When adding a new conftest entry, please use the correct format for", "        # specifying the relevant upstream Linux kernel commit.", "        #", "        # <function> was added|removed|etc by commit <sha> (\"<commit message\")", "        # in <kernel-version> (<commit date>).", "", "        *)", "            # Unknown test name given", "            echo \"Error: unknown conftest '$1' requested\" >&2", "            exit 1", "        ;;", "    esac", "}"] }
trace:   HunkApplier: hunk 1 applied at line 4646 (len=17), delta=12, target lines now=5102
  Applying Hunk 1/1...
debug:     Successfully applied Hunk 1 at line 4646 via Fuzzy { score: 0.8800000262260438 }
trace:     Replaced lines:
trace:       - 
trace:       -             compile_check_conftest "$CODE" "NV_ACPI_VIDEO_BACKLIGHT_USE_NATIVE" "" "functions"
trace:       -         ;;
trace:       - 
trace:       -         # When adding a new conftest entry, please use the correct format for
trace:       -         # specifying the relevant upstream Linux kernel commit.
trace:       -         #
trace:       -         # <function> was added|removed|etc by commit <sha> ("<commit message")
trace:       -         # in <kernel-version> (<commit date>).
trace:       - 
trace:       -         *)
trace:       -             # Unknown test name given
trace:       -             echo "Error: unknown conftest '$1' requested" >&2
trace:       -             exit 1
trace:       -         ;;
trace:       -     esac
trace:       - }
debug: HunkApplier::into_content: assembling final content from 5102 line(s) (touched_eof=false, patch_ends_with_newline=true, original_ends_with_newline=true)
trace: HunkApplier::into_content: resulting content has 179483 bytes (5102 lines, ends_with_newline=true)
  DRY RUN: Evaluated changes for 'conftest.sh' (1 hunks, clean=true)
trace:   Generating diff for dry run...
debug:   [2/2] Applying patch for 'nvidia/nvidia.Kbuild' (2 hunk(s))
Applying patch to: nvidia/nvidia.Kbuild
debug:   apply_patch_to_file: target_dir='.', hunks=2, dry_run=true, fuzz=0.70
trace:   Checking path safety for base '.' and relative path 'nvidia/nvidia.Kbuild'
trace:   ensure_path_is_safe: canonicalized base directory '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia")' on virtual path '<TARGET_DIR>'
trace:   ensure_path_is_safe: processing component 'Normal("nvidia.Kbuild")' on virtual path '<TARGET_DIR>/nvidia'
trace:   Path safety verified: 'nvidia/nvidia.Kbuild' safely resolves to '<TARGET_DIR>/nvidia/nvidia.Kbuild'
debug:   Resolved safe target path: '<TARGET_DIR>/nvidia/nvidia.Kbuild'
debug:   Target file exists: '<TARGET_DIR>/nvidia/nvidia.Kbuild'. Reading content...
trace:     Read 9107 bytes (221 lines) from target file.
debug:   Applying patch logic to content in-memory...
debug: apply_patch_to_content: patch for 'nvidia/nvidia.Kbuild' (2 hunks), original content: 9107 bytes
debug:   apply_patch_to_lines called with 221 lines of original content.
debug: resolve_hunk_line_hints: evaluating 2 hunk(s) across 221 target lines
trace: Hunk::get_match_block: extracted 7 match line(s)
trace:   Hunk 1: already has explicit line hint 105
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:   Hunk 2: already has explicit line hint 127
trace: resolve_hunk_line_hints: beginning relaxation pass 1
debug: resolve_hunk_line_hints: completed hint resolution. 2/2 hunk(s) have anchors.
debug: HunkApplier: initialized with 2 hunk(s) across 221 line(s) of target content (fuzz_factor=0.70, dry_run=true)
trace: HunkApplier::set_original_newline_status: original_ends_with_newline=true
debug: apply_hunk_to_lines: applying hunk with 8 line(s) against target with 221 line(s)
trace: Hunk::get_match_block: extracted 7 match line(s)
trace:   Match block: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += remap_pfn_range", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += hash__remap_4k_pfn", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += follow_pfn", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += vmap", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_pages_uc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += list_is_first", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_memory_uc"]
trace: Hunk::get_replace_block: extracted 7 replacement line(s)
trace:   Replace block: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += remap_pfn_range", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += hash__remap_4k_pfn", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += follow_pfn", "#NV_CONFTEST_FUNCTION_COMPILE_TESTS += vmap", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_pages_uc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += list_is_first", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_memory_uc"]
trace: Hunk::has_changes: true
trace: Hunk::get_match_block: extracted 7 match line(s)
trace: Hunk::required_match_span: calculated required match span as 1 line(s) (first_match_idx=Some(3), last_match_idx=Some(3))
trace: DefaultHunkFinder::find_candidate_locations: match block len=7, required_match_span=1, target lines=221
trace:   find_hunk_location_internal: match_block has 7 lines (entropy=true), target has 221 lines
trace:   find_hunk_location_internal called for a hunk with 7 lines to match against 221 target lines.
trace:     Attempting exact match for hunk (match block has 7 line(s))...
trace: tie_break_with_line_number: strategy='exact', hint=Some(105), entropy=true
trace:       No exact matches found.
trace:     Strategy 1 (Exact): no exact match found.
trace:     Attempting exact match (ignoring trailing whitespace) for hunk (match block has 7 line(s))...
trace: tie_break_with_line_number: strategy='exact (ignoring whitespace)', hint=Some(105), entropy=true
trace:       No exact (ignoring whitespace) matches found.
trace:     Strategy 2 (Whitespace-insensitive): no match found.
debug:     Strategy 3 (Fuzzy): beginning flexible window fuzzy search (threshold=0.70, match block len=0.7)
trace:       Hunk match block (7 lines): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += remap_pfn_range", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += hash__remap_4k_pfn", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += follow_pfn", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += vmap", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_pages_uc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += list_is_first", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_memory_uc"]
trace:       Searching with window sizes from 2 to 30 (hunk size: 7, fuzz distance: 23)
debug:       find_search_ranges: analyzing 7 match line(s) against 221 target line(s).
trace:         Identified 7 high-entropy candidate anchor line(s) (search_radius=15, max candidates to test=100)
debug:         Spatial consensus: 6 anchor(s) agree on start near line 113
debug:       Found anchor line (hunk line 2) with 1 occurrences.
trace:         Anchor text: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += hash__remap_4k_pfn'
trace:         Occurrence at target line 106: window estimated [90..149] (search radius +/-15)
trace:         Raw ranges before merging: [(89, 149)]
trace: merge_ranges: merging 1 input range(s): [(89, 149)]
trace: merge_ranges: result 1 disjoint range(s): [(89, 149)]
debug:       Search ranges merged: 1 disjoint range(s) covering 60/221 line(s) (72.9% pruned): [(89, 149)]
trace:     Using search ranges: [(89, 149)]
debug:       compute_scored_windows (parallel): evaluating 1305 candidate window(s) across 1 range(s) (window lengths 2..=30)
trace:         Match block length: 7, Target line count: 221, Search ranges: [(89, 149)]
trace:         score_window: window_len=14, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.154
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=15, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.166
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.567
trace:         score_window: window_len=16, match_len=7, line_score=0.134, ratio_lines=0.087, final_score=0.157
trace:         score_window: window_len=17, match_len=7, line_score=0.265, ratio_lines=0.167, final_score=0.297
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=18, match_len=7, line_score=0.395, ratio_lines=0.240, final_score=0.401
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.502
trace:         score_window: window_len=19, match_len=7, line_score=0.392, ratio_lines=0.231, final_score=0.474
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=20, match_len=7, line_score=0.518, ratio_lines=0.296, final_score=0.561
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=21, match_len=7, line_score=0.643, ratio_lines=0.357, final_score=0.643
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=13, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.166
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.569
trace:         score_window: window_len=14, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.179
trace:         score_window: window_len=15, match_len=7, line_score=0.135, ratio_lines=0.091, final_score=0.160
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=16, match_len=7, line_score=0.267, ratio_lines=0.174, final_score=0.302
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.613
trace:         score_window: window_len=17, match_len=7, line_score=0.398, ratio_lines=0.250, final_score=0.408
trace:         score_window: window_len=18, match_len=7, line_score=0.395, ratio_lines=0.240, final_score=0.482
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=19, match_len=7, line_score=0.522, ratio_lines=0.308, final_score=0.570
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=20, match_len=7, line_score=0.648, ratio_lines=0.370, final_score=0.649
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=12, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.167
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.534
trace:         score_window: window_len=13, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.181
trace:         score_window: window_len=14, match_len=7, line_score=0.136, ratio_lines=0.095, final_score=0.160
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=15, match_len=7, line_score=0.269, ratio_lines=0.182, final_score=0.303
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.507
trace:         score_window: window_len=16, match_len=7, line_score=0.401, ratio_lines=0.261, final_score=0.409
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=17, match_len=7, line_score=0.398, ratio_lines=0.250, final_score=0.483
trace:         score_window: window_len=18, match_len=7, line_score=0.527, ratio_lines=0.320, final_score=0.571
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=19, match_len=7, line_score=0.653, ratio_lines=0.385, final_score=0.653
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.615
trace:         score_window: window_len=13, match_len=7, line_score=0.137, ratio_lines=0.100, final_score=0.168
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.655
trace:         score_window: window_len=14, match_len=7, line_score=0.271, ratio_lines=0.190, final_score=0.316
trace:         score_window: window_len=15, match_len=7, line_score=0.404, ratio_lines=0.273, final_score=0.426
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=16, match_len=7, line_score=0.401, ratio_lines=0.261, final_score=0.502
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.609
trace:         score_window: window_len=17, match_len=7, line_score=0.531, ratio_lines=0.333, final_score=0.591
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=18, match_len=7, line_score=0.658, ratio_lines=0.400, final_score=0.672
trace:         score_window: window_len=12, match_len=7, line_score=0.138, ratio_lines=0.105, final_score=0.177
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=13, match_len=7, line_score=0.273, ratio_lines=0.200, final_score=0.331
trace:         score_window: window_len=14, match_len=7, line_score=0.407, ratio_lines=0.286, final_score=0.445
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=15, match_len=7, line_score=0.404, ratio_lines=0.273, final_score=0.523
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.534
trace:         score_window: window_len=16, match_len=7, line_score=0.535, ratio_lines=0.348, final_score=0.615
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.594
trace:         score_window: window_len=17, match_len=7, line_score=0.663, ratio_lines=0.417, final_score=0.697
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.495
trace:         score_window: window_len=11, match_len=7, line_score=0.139, ratio_lines=0.111, final_score=0.177
trace:         score_window: window_len=12, match_len=7, line_score=0.276, ratio_lines=0.211, final_score=0.332
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.555
trace:         score_window: window_len=13, match_len=7, line_score=0.410, ratio_lines=0.300, final_score=0.446
trace:         score_window: window_len=14, match_len=7, line_score=0.407, ratio_lines=0.286, final_score=0.524
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.523
trace:         score_window: window_len=15, match_len=7, line_score=0.539, ratio_lines=0.364, final_score=0.616
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.644
trace:         score_window: window_len=16, match_len=7, line_score=0.668, ratio_lines=0.435, final_score=0.699
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=11, match_len=7, line_score=0.278, ratio_lines=0.222, final_score=0.370
trace:         score_window: window_len=12, match_len=7, line_score=0.413, ratio_lines=0.316, final_score=0.493
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.597
trace:         score_window: window_len=13, match_len=7, line_score=0.410, ratio_lines=0.300, final_score=0.576
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.510
trace:         score_window: window_len=14, match_len=7, line_score=0.543, ratio_lines=0.381, final_score=0.673
trace:         score_window: window_len=15, match_len=7, line_score=0.673, ratio_lines=0.455, final_score=0.759
trace:         score_window: window_len=10, match_len=7, line_score=0.280, ratio_lines=0.235, final_score=0.280
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.645
trace:         score_window: window_len=11, match_len=7, line_score=0.416, ratio_lines=0.333, final_score=0.505
trace:         score_window: window_len=12, match_len=7, line_score=0.413, ratio_lines=0.316, final_score=0.589
trace:         score_window: window_len=13, match_len=7, line_score=0.547, ratio_lines=0.400, final_score=0.687
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.609
trace:         score_window: window_len=14, match_len=7, line_score=0.679, ratio_lines=0.476, final_score=0.774
trace:         score_window: window_len=9, match_len=7, line_score=0.282, ratio_lines=0.250, final_score=0.282
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=10, match_len=7, line_score=0.419, ratio_lines=0.353, final_score=0.507
trace:         score_window: window_len=11, match_len=7, line_score=0.416, ratio_lines=0.333, final_score=0.591
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.589
trace:         score_window: window_len=12, match_len=7, line_score=0.551, ratio_lines=0.421, final_score=0.689
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=13, match_len=7, line_score=0.684, ratio_lines=0.500, final_score=0.776
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.516
trace:         score_window: window_len=8, match_len=7, line_score=0.284, ratio_lines=0.267, final_score=0.284
trace:         score_window: window_len=9, match_len=7, line_score=0.422, ratio_lines=0.375, final_score=0.509
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=10, match_len=7, line_score=0.419, ratio_lines=0.353, final_score=0.593
trace:         score_window: window_len=11, match_len=7, line_score=0.555, ratio_lines=0.444, final_score=0.691
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=12, match_len=7, line_score=0.689, ratio_lines=0.526, final_score=0.779
trace:         score_window: window_len=7, match_len=7, line_score=0.286, ratio_lines=0.286, final_score=0.294
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=8, match_len=7, line_score=0.426, ratio_lines=0.400, final_score=0.513
trace:         score_window: window_len=9, match_len=7, line_score=0.422, ratio_lines=0.375, final_score=0.596
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.571
trace:         score_window: window_len=10, match_len=7, line_score=0.559, ratio_lines=0.471, final_score=0.695
trace:         score_window: window_len=11, match_len=7, line_score=0.694, ratio_lines=0.556, final_score=0.783
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.588
trace:         score_window: window_len=7, match_len=7, line_score=0.429, ratio_lines=0.429, final_score=0.549
trace:         score_window: window_len=6, match_len=7, line_score=0.308, ratio_lines=0.308, final_score=0.349
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.622
trace:         score_window: window_len=8, match_len=7, line_score=0.426, ratio_lines=0.400, final_score=0.635
trace:         score_window: window_len=9, match_len=7, line_score=0.563, ratio_lines=0.500, final_score=0.737
trace:         score_window: window_len=10, match_len=7, line_score=0.699, ratio_lines=0.588, final_score=0.743
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=7, match_len=7, line_score=0.429, ratio_lines=0.429, final_score=0.639
trace:         score_window: window_len=6, match_len=7, line_score=0.462, ratio_lines=0.462, final_score=0.553
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=8, match_len=7, line_score=0.567, ratio_lines=0.533, final_score=0.742
trace:         score_window: window_len=5, match_len=7, line_score=0.333, ratio_lines=0.333, final_score=0.361
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=7, match_len=7, line_score=0.571, ratio_lines=0.571, final_score=0.745
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.534
trace:         score_window: window_len=6, match_len=7, line_score=0.462, ratio_lines=0.462, final_score=0.642
trace:         score_window: window_len=5, match_len=7, line_score=0.500, ratio_lines=0.500, final_score=0.557
trace:         score_window: window_len=4, match_len=7, line_score=0.364, ratio_lines=0.364, final_score=0.375
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=6, match_len=7, line_score=0.615, ratio_lines=0.615, final_score=0.737
trace:         score_window: window_len=5, match_len=7, line_score=0.500, ratio_lines=0.500, final_score=0.700
trace:         score_window: window_len=4, match_len=7, line_score=0.545, ratio_lines=0.545, final_score=0.567
trace:         score_window: window_len=3, match_len=7, line_score=0.400, ratio_lines=0.400, final_score=0.411
trace:         score_window: window_len=2, match_len=7, line_score=0.222, ratio_lines=0.222, final_score=0.222
trace:         score_window: window_len=5, match_len=7, line_score=0.667, ratio_lines=0.667, final_score=0.760
trace:         score_window: window_len=4, match_len=7, line_score=0.545, ratio_lines=0.545, final_score=0.704
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.512
trace:         score_window: window_len=3, match_len=7, line_score=0.600, ratio_lines=0.600, final_score=0.600
trace:         score_window: window_len=2, match_len=7, line_score=0.444, ratio_lines=0.444, final_score=0.444
trace:         score_window: window_len=5, match_len=7, line_score=0.667, ratio_lines=0.667, final_score=0.760
trace:         score_window: window_len=4, match_len=7, line_score=0.545, ratio_lines=0.545, final_score=0.698
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=10, match_len=7, line_score=0.699, ratio_lines=0.588, final_score=0.699
trace:         score_window: window_len=3, match_len=7, line_score=0.400, ratio_lines=0.400, final_score=0.506
trace:         score_window: window_len=11, match_len=7, line_score=0.694, ratio_lines=0.556, final_score=0.694
trace:         score_window: window_len=2, match_len=7, line_score=0.444, ratio_lines=0.444, final_score=0.444
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=12, match_len=7, line_score=0.689, ratio_lines=0.526, final_score=0.689
trace:         score_window: window_len=13, match_len=7, line_score=0.684, ratio_lines=0.500, final_score=0.684
trace:         score_window: window_len=14, match_len=7, line_score=0.679, ratio_lines=0.476, final_score=0.679
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=15, match_len=7, line_score=0.673, ratio_lines=0.455, final_score=0.673
trace:         score_window: window_len=16, match_len=7, line_score=0.668, ratio_lines=0.435, final_score=0.668
trace:         score_window: window_len=17, match_len=7, line_score=0.663, ratio_lines=0.417, final_score=0.663
trace:         score_window: window_len=18, match_len=7, line_score=0.658, ratio_lines=0.400, final_score=0.658
trace:         score_window: window_len=19, match_len=7, line_score=0.653, ratio_lines=0.385, final_score=0.653
trace:         score_window: window_len=20, match_len=7, line_score=0.648, ratio_lines=0.370, final_score=0.648
trace:         score_window: window_len=21, match_len=7, line_score=0.643, ratio_lines=0.357, final_score=0.643
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.534
trace:         score_window: window_len=22, match_len=7, line_score=0.638, ratio_lines=0.345, final_score=0.638
trace:         score_window: window_len=23, match_len=7, line_score=0.633, ratio_lines=0.333, final_score=0.633
trace:         score_window: window_len=24, match_len=7, line_score=0.628, ratio_lines=0.323, final_score=0.628
trace:         score_window: window_len=25, match_len=7, line_score=0.622, ratio_lines=0.312, final_score=0.622
trace:         score_window: window_len=26, match_len=7, line_score=0.617, ratio_lines=0.303, final_score=0.617
trace:         score_window: window_len=27, match_len=7, line_score=0.612, ratio_lines=0.294, final_score=0.612
trace:         score_window: window_len=28, match_len=7, line_score=0.607, ratio_lines=0.286, final_score=0.607
trace:         score_window: window_len=29, match_len=7, line_score=0.602, ratio_lines=0.278, final_score=0.602
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=30, match_len=7, line_score=0.597, ratio_lines=0.270, final_score=0.597
trace:         score_window: window_len=7, match_len=7, line_score=0.571, ratio_lines=0.571, final_score=0.674
trace:         score_window: window_len=6, match_len=7, line_score=0.615, ratio_lines=0.615, final_score=0.700
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.480
trace:         score_window: window_len=8, match_len=7, line_score=0.567, ratio_lines=0.533, final_score=0.629
trace:         score_window: window_len=5, match_len=7, line_score=0.667, ratio_lines=0.667, final_score=0.760
trace:         score_window: window_len=9, match_len=7, line_score=0.563, ratio_lines=0.500, final_score=0.587
trace:         score_window: window_len=4, match_len=7, line_score=0.545, ratio_lines=0.545, final_score=0.645
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=10, match_len=7, line_score=0.559, ratio_lines=0.471, final_score=0.559
trace:         score_window: window_len=3, match_len=7, line_score=0.400, ratio_lines=0.400, final_score=0.506
trace:         score_window: window_len=4, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.424
trace:         score_window: window_len=11, match_len=7, line_score=0.555, ratio_lines=0.444, final_score=0.555
trace:         score_window: window_len=2, match_len=7, line_score=0.222, ratio_lines=0.222, final_score=0.336
trace:         score_window: window_len=12, match_len=7, line_score=0.551, ratio_lines=0.421, final_score=0.551
trace:         score_window: window_len=13, match_len=7, line_score=0.547, ratio_lines=0.400, final_score=0.547
trace:         score_window: window_len=14, match_len=7, line_score=0.543, ratio_lines=0.381, final_score=0.543
trace:         score_window: window_len=15, match_len=7, line_score=0.539, ratio_lines=0.364, final_score=0.539
trace:         score_window: window_len=16, match_len=7, line_score=0.535, ratio_lines=0.348, final_score=0.535
trace:         score_window: window_len=17, match_len=7, line_score=0.531, ratio_lines=0.333, final_score=0.531
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=18, match_len=7, line_score=0.527, ratio_lines=0.320, final_score=0.527
trace:         score_window: window_len=19, match_len=7, line_score=0.522, ratio_lines=0.308, final_score=0.522
trace:         score_window: window_len=20, match_len=7, line_score=0.518, ratio_lines=0.296, final_score=0.518
trace:         score_window: window_len=21, match_len=7, line_score=0.514, ratio_lines=0.286, final_score=0.514
trace:         score_window: window_len=22, match_len=7, line_score=0.510, ratio_lines=0.276, final_score=0.510
trace:         score_window: window_len=23, match_len=7, line_score=0.506, ratio_lines=0.267, final_score=0.506
trace:         score_window: window_len=24, match_len=7, line_score=0.502, ratio_lines=0.258, final_score=0.502
trace:         score_window: window_len=25, match_len=7, line_score=0.498, ratio_lines=0.250, final_score=0.498
trace:         score_window: window_len=26, match_len=7, line_score=0.494, ratio_lines=0.242, final_score=0.494
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=27, match_len=7, line_score=0.490, ratio_lines=0.235, final_score=0.490
trace:         score_window: window_len=28, match_len=7, line_score=0.486, ratio_lines=0.229, final_score=0.486
trace:         score_window: window_len=29, match_len=7, line_score=0.482, ratio_lines=0.222, final_score=0.482
trace:         score_window: window_len=30, match_len=7, line_score=0.478, ratio_lines=0.216, final_score=0.478
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.534
trace:         score_window: window_len=7, match_len=7, line_score=0.429, ratio_lines=0.429, final_score=0.535
trace:         score_window: window_len=6, match_len=7, line_score=0.462, ratio_lines=0.462, final_score=0.577
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=8, match_len=7, line_score=0.426, ratio_lines=0.400, final_score=0.497
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.493
trace:         score_window: window_len=5, match_len=7, line_score=0.500, ratio_lines=0.500, final_score=0.628
trace:         score_window: window_len=9, match_len=7, line_score=0.422, ratio_lines=0.375, final_score=0.466
trace:         score_window: window_len=4, match_len=7, line_score=0.545, ratio_lines=0.545, final_score=0.645
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=4, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.535
trace:         score_window: window_len=10, match_len=7, line_score=0.419, ratio_lines=0.353, final_score=0.438
trace:         score_window: window_len=3, match_len=7, line_score=0.400, ratio_lines=0.400, final_score=0.506
trace:         score_window: window_len=11, match_len=7, line_score=0.416, ratio_lines=0.333, final_score=0.416
trace:         score_window: window_len=2, match_len=7, line_score=0.222, ratio_lines=0.222, final_score=0.336
trace:         score_window: window_len=12, match_len=7, line_score=0.413, ratio_lines=0.316, final_score=0.413
trace:         score_window: window_len=13, match_len=7, line_score=0.410, ratio_lines=0.300, final_score=0.410
trace:         score_window: window_len=14, match_len=7, line_score=0.407, ratio_lines=0.286, final_score=0.407
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=15, match_len=7, line_score=0.404, ratio_lines=0.273, final_score=0.404
trace:         score_window: window_len=16, match_len=7, line_score=0.401, ratio_lines=0.261, final_score=0.401
trace:         score_window: window_len=17, match_len=7, line_score=0.398, ratio_lines=0.250, final_score=0.398
trace:         score_window: window_len=18, match_len=7, line_score=0.395, ratio_lines=0.240, final_score=0.395
trace:         score_window: window_len=19, match_len=7, line_score=0.392, ratio_lines=0.231, final_score=0.392
trace:         score_window: window_len=20, match_len=7, line_score=0.389, ratio_lines=0.222, final_score=0.389
trace:         score_window: window_len=21, match_len=7, line_score=0.386, ratio_lines=0.214, final_score=0.386
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=7, match_len=7, line_score=0.429, ratio_lines=0.429, final_score=0.429
trace:         score_window: window_len=6, match_len=7, line_score=0.462, ratio_lines=0.462, final_score=0.462
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.534
trace:         score_window: window_len=8, match_len=7, line_score=0.426, ratio_lines=0.400, final_score=0.426
trace:         score_window: window_len=5, match_len=7, line_score=0.500, ratio_lines=0.500, final_score=0.500
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=9, match_len=7, line_score=0.422, ratio_lines=0.375, final_score=0.422
trace:         score_window: window_len=4, match_len=7, line_score=0.545, ratio_lines=0.545, final_score=0.545
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.480
trace:         score_window: window_len=10, match_len=7, line_score=0.419, ratio_lines=0.353, final_score=0.419
trace:         score_window: window_len=3, match_len=7, line_score=0.600, ratio_lines=0.600, final_score=0.600
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=11, match_len=7, line_score=0.416, ratio_lines=0.333, final_score=0.416
trace:         score_window: window_len=2, match_len=7, line_score=0.444, ratio_lines=0.444, final_score=0.444
trace:         score_window: window_len=12, match_len=7, line_score=0.413, ratio_lines=0.316, final_score=0.413
trace:         score_window: window_len=13, match_len=7, line_score=0.410, ratio_lines=0.300, final_score=0.410
trace:         score_window: window_len=14, match_len=7, line_score=0.407, ratio_lines=0.286, final_score=0.407
trace:         score_window: window_len=15, match_len=7, line_score=0.404, ratio_lines=0.273, final_score=0.404
trace:         score_window: window_len=16, match_len=7, line_score=0.401, ratio_lines=0.261, final_score=0.401
trace:         score_window: window_len=17, match_len=7, line_score=0.398, ratio_lines=0.250, final_score=0.398
trace:         score_window: window_len=18, match_len=7, line_score=0.395, ratio_lines=0.240, final_score=0.395
trace:         score_window: window_len=19, match_len=7, line_score=0.392, ratio_lines=0.231, final_score=0.392
trace:         score_window: window_len=20, match_len=7, line_score=0.389, ratio_lines=0.222, final_score=0.389
trace:         score_window: window_len=21, match_len=7, line_score=0.386, ratio_lines=0.214, final_score=0.386
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=7, match_len=7, line_score=0.286, ratio_lines=0.286, final_score=0.286
trace:         score_window: window_len=6, match_len=7, line_score=0.308, ratio_lines=0.308, final_score=0.308
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=8, match_len=7, line_score=0.284, ratio_lines=0.267, final_score=0.284
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.534
trace:         score_window: window_len=5, match_len=7, line_score=0.333, ratio_lines=0.333, final_score=0.333
trace:         score_window: window_len=9, match_len=7, line_score=0.282, ratio_lines=0.250, final_score=0.282
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=4, match_len=7, line_score=0.364, ratio_lines=0.364, final_score=0.364
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.480
trace:         score_window: window_len=10, match_len=7, line_score=0.280, ratio_lines=0.235, final_score=0.280
trace:         score_window: window_len=3, match_len=7, line_score=0.400, ratio_lines=0.400, final_score=0.400
trace:         score_window: window_len=11, match_len=7, line_score=0.278, ratio_lines=0.222, final_score=0.278
trace:         score_window: window_len=2, match_len=7, line_score=0.444, ratio_lines=0.444, final_score=0.444
trace:         score_window: window_len=12, match_len=7, line_score=0.276, ratio_lines=0.211, final_score=0.276
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=7, match_len=7, line_score=0.143, ratio_lines=0.143, final_score=0.623
trace:         score_window: window_len=4, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.416
trace:         score_window: window_len=6, match_len=7, line_score=0.154, ratio_lines=0.154, final_score=0.580
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=8, match_len=7, line_score=0.142, ratio_lines=0.133, final_score=0.581
trace:         score_window: window_len=5, match_len=7, line_score=0.167, ratio_lines=0.167, final_score=0.530
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=9, match_len=7, line_score=0.141, ratio_lines=0.125, final_score=0.544
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.661
trace:         score_window: window_len=10, match_len=7, line_score=0.140, ratio_lines=0.118, final_score=0.511
trace:         score_window: window_len=2, match_len=7, line_score=0.222, ratio_lines=0.222, final_score=0.309
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.596
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.534
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.480
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.534
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.706
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.624
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.653
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.661
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.595
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.525
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.626
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.534
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.617
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.480
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.663
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.557
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.583
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.601
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.612
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.534
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.611
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.597
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.480
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.550
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.653
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.496
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.606
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.552
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.635
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.599
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.564
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.692
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.661
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.496
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.590
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.640
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.598
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.638
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.602
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.603
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.736
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.679
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.534
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.678
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.480
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.606
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.635
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.534
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.596
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.480
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.716
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.681
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.608
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.534
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.480
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.676
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.534
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.621
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.480
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=7, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.580
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.534
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.480
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.534
trace:         score_window: window_len=4, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.416
trace:         score_window: window_len=8, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=6, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.534
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.494
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.605
trace:         score_window: window_len=4, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.423
trace:         score_window: window_len=5, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.480
trace:         score_window: window_len=9, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=10, match_len=7, line_score=0.000, ratio_lines=0.000, final_score=0.476
debug:       compute_scored_windows (parallel) complete: scored 1305 window(s). Best candidate score=0.857 at line 105 (len=7).
trace:       Top fuzzy match candidates:
trace:         - Index 104, Len 7: Score 0.857 (Ratio 0.857) | Content: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += remap_pfn_range", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += hash__remap_4k_pfn", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += follow_pfn", "#NV_CONFTEST_FUNCTION_COMPILE_TESTS += vmap", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_pages_uc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += list_is_first", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_memory_uc"]
trace:         - Index 103, Len 8: Score 0.851 (Ratio 0.851) | Content: ["", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += remap_pfn_range", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += hash__remap_4k_pfn", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += follow_pfn", "#NV_CONFTEST_FUNCTION_COMPILE_TESTS += vmap", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_pages_uc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += list_is_first", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_memory_uc"]
trace:         - Index 104, Len 8: Score 0.851 (Ratio 0.851) | Content: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += remap_pfn_range", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += hash__remap_4k_pfn", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += follow_pfn", "#NV_CONFTEST_FUNCTION_COMPILE_TESTS += vmap", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_pages_uc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += list_is_first", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_memory_uc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_memory_array_uc"]
trace:         - Index 102, Len 9: Score 0.845 (Ratio 0.845) | Content: ["NV_OBJECTS_DEPEND_ON_CONFTEST += $(NVIDIA_OBJECTS)", "", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += remap_pfn_range", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += hash__remap_4k_pfn", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += follow_pfn", "#NV_CONFTEST_FUNCTION_COMPILE_TESTS += vmap", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_pages_uc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += list_is_first", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_memory_uc"]
trace:         - Index 103, Len 9: Score 0.845 (Ratio 0.845) | Content: ["", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += remap_pfn_range", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += hash__remap_4k_pfn", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += follow_pfn", "#NV_CONFTEST_FUNCTION_COMPILE_TESTS += vmap", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_pages_uc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += list_is_first", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_memory_uc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_memory_array_uc"]
trace:         New best score: 0.541 (ratio 0.541 [l:0.000,w:0.000]) at index 89 (window len 7)
trace:         Tie in score (0.541) and ratio (0.541). Adding candidate: index 89, len 8
trace:         Tie in score (0.541) and ratio (0.541). Adding candidate: index 89, len 9
trace:         New best score: 0.544 (ratio 0.544 [l:0.000,w:0.000]) at index 89 (window len 10)
trace:         New best score: 0.636 (ratio 0.636 [l:0.000,w:0.000]) at index 89 (window len 11)
trace:         New best score: 0.638 (ratio 0.638 [l:0.000,w:0.000]) at index 89 (window len 12)
trace:         Tie in score (0.638) and ratio (0.638). Adding candidate: index 89, len 13
trace:         New best score: 0.643 (ratio 0.643 [l:0.357,w:0.500]) at index 89 (window len 21)
trace:         New best score: 0.765 (ratio 0.765 [l:0.414,w:0.765]) at index 89 (window len 22)
trace:         New best score: 0.771 (ratio 0.771 [l:0.429,w:0.771]) at index 90 (window len 21)
trace:         New best score: 0.778 (ratio 0.778 [l:0.444,w:0.778]) at index 91 (window len 20)
trace:         New best score: 0.784 (ratio 0.784 [l:0.462,w:0.784]) at index 92 (window len 19)
trace:         New best score: 0.790 (ratio 0.790 [l:0.480,w:0.790]) at index 93 (window len 18)
trace:         New best score: 0.796 (ratio 0.796 [l:0.500,w:0.796]) at index 94 (window len 17)
trace:         New best score: 0.802 (ratio 0.802 [l:0.522,w:0.802]) at index 95 (window len 16)
trace:         New best score: 0.808 (ratio 0.808 [l:0.545,w:0.808]) at index 96 (window len 15)
trace:         New best score: 0.814 (ratio 0.814 [l:0.571,w:0.814]) at index 97 (window len 14)
trace:         New best score: 0.820 (ratio 0.820 [l:0.600,w:0.820]) at index 98 (window len 13)
trace:         New best score: 0.827 (ratio 0.827 [l:0.632,w:0.827]) at index 99 (window len 12)
trace:         New best score: 0.833 (ratio 0.833 [l:0.667,w:0.833]) at index 100 (window len 11)
trace:         New best score: 0.839 (ratio 0.839 [l:0.706,w:0.839]) at index 101 (window len 10)
trace:         New best score: 0.845 (ratio 0.845 [l:0.750,w:0.845]) at index 102 (window len 9)
trace:         New best score: 0.851 (ratio 0.851 [l:0.800,w:0.851]) at index 103 (window len 8)
trace:         New best score: 0.857 (ratio 0.857 [l:0.857,w:0.857]) at index 104 (window len 7)
debug:     Strategy 3 (Fuzzy): 290 window(s) met threshold 0.70
trace:       Top 3 passing candidates: [("0.857", 105, 7), ("0.851", 104, 8), ("0.851", 105, 8)]
debug:     Top fuzzy candidate: start line 105 (len=7, score=0.857)
trace:       Adding candidate location at line 104 (len=8, score=0.851)
trace:       Adding candidate location at line 105 (len=8, score=0.851)
trace:       Adding candidate location at line 103 (len=9, score=0.845)
trace:       Adding candidate location at line 104 (len=9, score=0.845)
trace:       Adding candidate location at line 105 (len=9, score=0.845)
trace:       Adding candidate location at line 102 (len=10, score=0.839)
trace:       Adding candidate location at line 103 (len=10, score=0.839)
trace:       Adding candidate location at line 104 (len=10, score=0.839)
trace:       Adding candidate location at line 105 (len=10, score=0.839)
trace:       Adding candidate location at line 101 (len=11, score=0.833)
trace:       Adding candidate location at line 102 (len=11, score=0.833)
trace:       Adding candidate location at line 103 (len=11, score=0.833)
trace:       Adding candidate location at line 104 (len=11, score=0.833)
trace:       Adding candidate location at line 105 (len=11, score=0.833)
trace:       Adding candidate location at line 100 (len=12, score=0.827)
trace:       Adding candidate location at line 101 (len=12, score=0.827)
trace:       Adding candidate location at line 102 (len=12, score=0.827)
trace:       Adding candidate location at line 103 (len=12, score=0.827)
trace:       Adding candidate location at line 104 (len=12, score=0.827)
trace:       Reached maximum candidate limit (20), stopping candidate collection
debug:     Strategy 3 (Fuzzy): selected 20 candidate location(s)
trace:   Pruned candidates by min_span 1: 20 -> 20 candidate(s)
trace: DefaultHunkFinder::find_candidate_locations: returning 20 candidate(s)
debug:   Found 20 candidate location(s) for hunk. Testing sequentially...
trace:   Evaluating candidate 1/20 at location HunkLocation { start_index: 104, length: 7 } (match_type: Fuzzy { score: 0.8571428656578064 })
debug:   Found location HunkLocation { start_index: 104, length: 7 } with match type Fuzzy { score: 0.8571428656578064 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 105 (length 7), match_type=Fuzzy { score: 0.8571428656578064 }, total target lines=221.
trace: Hunk::get_match_block: extracted 7 match line(s)
trace:     Match block lines: 7 | Total hunk lines: 8
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += remap_pfn_range", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += hash__remap_4k_pfn", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += follow_pfn", "#NV_CONFTEST_FUNCTION_COMPILE_TESTS += vmap", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_pages_uc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += list_is_first", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_memory_uc"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=104, len=7
trace:       File content in matched range (7 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += remap_pfn_range", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += hash__remap_4k_pfn", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += follow_pfn", "#NV_CONFTEST_FUNCTION_COMPILE_TESTS += vmap", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_pages_uc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += list_is_first", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_memory_uc"]
trace:       Parsed hunk: 7 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 7 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.857
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 3 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += remap_pfn_range'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += hash__remap_4k_pfn'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += follow_pfn'
trace:       DiffOp::Replace: hunk lines 3..4 (len=1) vs file lines 3..4 (len=1)
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace:         1-to-1 replacement line validation [line 3]: is_removal=true, word_sim=0.800, char_sim=0.988
trace:         Replace (1-to-1): removing line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += vmap'
trace:         Replace (1-to-1): applied addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += vmap'
trace:       DiffOp::Equal: 3 line(s) aligned (hunk old_idx=4, file new_idx=4)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_pages_uc'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += list_is_first'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_memory_uc'
debug:     Robust reconstruction complete: produced 7 replacement line(s) for 7 target line(s).
trace:   Splicing final replacement block into target lines: range [104..111], replacement line count=7
  try_apply_hunk_at_location: successfully spliced hunk at line 105 (replaced 7 line(s), resulting target lines=221)
trace:     Replaced lines: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += remap_pfn_range", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += hash__remap_4k_pfn", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += follow_pfn", "#NV_CONFTEST_FUNCTION_COMPILE_TESTS += vmap", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_pages_uc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += list_is_first", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_memory_uc"]
debug:   Candidate 1/20 at HunkLocation { start_index: 104, length: 7 } succeeded! Hunk applied cleanly.
debug:   HunkApplier: hunk 1 application outcome: Applied { location: HunkLocation { start_index: 104, length: 7 }, match_type: Fuzzy { score: 0.8571428656578064 }, replaced_lines: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += remap_pfn_range", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += hash__remap_4k_pfn", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += follow_pfn", "#NV_CONFTEST_FUNCTION_COMPILE_TESTS += vmap", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_pages_uc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += list_is_first", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_memory_uc"] }
trace:   HunkApplier: hunk 1 applied at line 105 (len=7), delta=0, target lines now=221
  Applying Hunk 1/2...
debug:     Successfully applied Hunk 1 at line 105 via Fuzzy { score: 0.8571428656578064 }
trace:     Replaced lines:
trace:       - NV_CONFTEST_FUNCTION_COMPILE_TESTS += remap_pfn_range
trace:       - NV_CONFTEST_FUNCTION_COMPILE_TESTS += hash__remap_4k_pfn
trace:       - NV_CONFTEST_FUNCTION_COMPILE_TESTS += follow_pfn
trace:       - #NV_CONFTEST_FUNCTION_COMPILE_TESTS += vmap
trace:       - NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_pages_uc
trace:       - NV_CONFTEST_FUNCTION_COMPILE_TESTS += list_is_first
trace:       - NV_CONFTEST_FUNCTION_COMPILE_TESTS += set_memory_uc
debug: apply_hunk_to_lines: applying hunk with 10 line(s) against target with 221 line(s)
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:   Match block: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "- ", "2.20.1"]
trace: Hunk::get_replace_block: extracted 8 replacement line(s)
trace:   Replace block: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "2.20.1"]
trace: Hunk::has_changes: true
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: Hunk::required_match_span: calculated required match span as 5 line(s) (first_match_idx=Some(3), last_match_idx=Some(7))
trace: DefaultHunkFinder::find_candidate_locations: match block len=9, required_match_span=5, target lines=221
trace:   find_hunk_location_internal: match_block has 9 lines (entropy=true), target has 221 lines
trace:   find_hunk_location_internal called for a hunk with 9 lines to match against 221 target lines.
trace:     Attempting exact match for hunk (match block has 9 line(s))...
trace: tie_break_with_line_number: strategy='exact', hint=Some(127), entropy=true
trace:       No exact matches found.
trace:     Strategy 1 (Exact): no exact match found.
trace:     Attempting exact match (ignoring trailing whitespace) for hunk (match block has 9 line(s))...
trace: tie_break_with_line_number: strategy='exact (ignoring whitespace)', hint=Some(127), entropy=true
trace:       No exact (ignoring whitespace) matches found.
trace:     Strategy 2 (Whitespace-insensitive): no match found.
debug:     Strategy 3 (Fuzzy): beginning flexible window fuzzy search (threshold=0.70, match block len=0.7)
trace:       Hunk match block (9 lines): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "- ", "2.20.1"]
trace:       Searching with window sizes from 5 to 33 (hunk size: 9, fuzz distance: 24)
debug:       find_search_ranges: analyzing 9 match line(s) against 221 target line(s).
trace:         Identified 8 high-entropy candidate anchor line(s) (search_radius=18, max candidates to test=100)
debug:         Spatial consensus: 7 anchor(s) agree on start near line 138
debug:       Found anchor line (hunk line 5) with 1 occurrences.
trace:         Anchor text: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Occurrence at target line 131: window estimated [109..177] (search radius +/-18)
trace:         Raw ranges before merging: [(108, 177)]
trace: merge_ranges: merging 1 input range(s): [(108, 177)]
trace: merge_ranges: result 1 disjoint range(s): [(108, 177)]
debug:       Search ranges merged: 1 disjoint range(s) covering 69/221 line(s) (68.8% pruned): [(108, 177)]
trace:     Using search ranges: [(108, 177)]
debug:       compute_scored_windows (parallel): evaluating 1479 candidate window(s) across 1 range(s) (window lengths 5..=33)
trace:         Match block length: 9, Target line count: 221, Search ranges: [(108, 177)]
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.574
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.507
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.668
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.611
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.509
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.481
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.618
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.548
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.555
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.479
trace:         score_window: window_len=22, match_len=9, line_score=0.412, ratio_lines=0.258, final_score=0.412
trace:         score_window: window_len=23, match_len=9, line_score=0.512, ratio_lines=0.312, final_score=0.512
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.480
trace:         score_window: window_len=24, match_len=9, line_score=0.611, ratio_lines=0.364, final_score=0.611
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.539
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.713
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.663
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.599
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.458
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.481
trace:         score_window: window_len=21, match_len=9, line_score=0.415, ratio_lines=0.267, final_score=0.415
trace:         score_window: window_len=22, match_len=9, line_score=0.515, ratio_lines=0.323, final_score=0.515
trace:         score_window: window_len=23, match_len=9, line_score=0.615, ratio_lines=0.375, final_score=0.615
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.660
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.603
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.458
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.552
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.593
trace:         score_window: window_len=19, match_len=9, line_score=0.315, ratio_lines=0.214, final_score=0.315
trace:         score_window: window_len=20, match_len=9, line_score=0.417, ratio_lines=0.276, final_score=0.417
trace:         score_window: window_len=21, match_len=9, line_score=0.519, ratio_lines=0.333, final_score=0.519
trace:         score_window: window_len=22, match_len=9, line_score=0.619, ratio_lines=0.387, final_score=0.619
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.606
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.610
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.576
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.579
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.458
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.498
trace:         score_window: window_len=18, match_len=9, line_score=0.317, ratio_lines=0.222, final_score=0.317
trace:         score_window: window_len=19, match_len=9, line_score=0.420, ratio_lines=0.286, final_score=0.420
trace:         score_window: window_len=20, match_len=9, line_score=0.522, ratio_lines=0.345, final_score=0.522
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.646
trace:         score_window: window_len=21, match_len=9, line_score=0.622, ratio_lines=0.400, final_score=0.622
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.593
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.538
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.568
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.458
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.595
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.454
trace:         score_window: window_len=17, match_len=9, line_score=0.319, ratio_lines=0.231, final_score=0.319
trace:         score_window: window_len=18, match_len=9, line_score=0.422, ratio_lines=0.296, final_score=0.422
trace:         score_window: window_len=19, match_len=9, line_score=0.525, ratio_lines=0.357, final_score=0.525
trace:         score_window: window_len=20, match_len=9, line_score=0.626, ratio_lines=0.414, final_score=0.626
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.454
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.458
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.502
trace:         score_window: window_len=16, match_len=9, line_score=0.320, ratio_lines=0.240, final_score=0.320
trace:         score_window: window_len=17, match_len=9, line_score=0.425, ratio_lines=0.308, final_score=0.425
trace:         score_window: window_len=18, match_len=9, line_score=0.528, ratio_lines=0.370, final_score=0.528
trace:         score_window: window_len=19, match_len=9, line_score=0.630, ratio_lines=0.429, final_score=0.630
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.598
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.637
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.596
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.458
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.552
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.554
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.591
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.601
trace:         score_window: window_len=15, match_len=9, line_score=0.322, ratio_lines=0.250, final_score=0.322
trace:         score_window: window_len=16, match_len=9, line_score=0.427, ratio_lines=0.320, final_score=0.427
trace:         score_window: window_len=17, match_len=9, line_score=0.531, ratio_lines=0.385, final_score=0.531
trace:         score_window: window_len=18, match_len=9, line_score=0.633, ratio_lines=0.444, final_score=0.633
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.498
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.483
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.458
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.535
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.583
trace:         score_window: window_len=14, match_len=9, line_score=0.324, ratio_lines=0.261, final_score=0.324
trace:         score_window: window_len=15, match_len=9, line_score=0.430, ratio_lines=0.333, final_score=0.430
trace:         score_window: window_len=16, match_len=9, line_score=0.534, ratio_lines=0.400, final_score=0.534
trace:         score_window: window_len=17, match_len=9, line_score=0.637, ratio_lines=0.462, final_score=0.637
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.454
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.531
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.564
trace:         score_window: window_len=11, match_len=9, line_score=0.110, ratio_lines=0.100, final_score=0.488
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.501
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=13, match_len=9, line_score=0.326, ratio_lines=0.273, final_score=0.326
trace:         score_window: window_len=14, match_len=9, line_score=0.432, ratio_lines=0.348, final_score=0.432
trace:         score_window: window_len=15, match_len=9, line_score=0.537, ratio_lines=0.417, final_score=0.537
trace:         score_window: window_len=16, match_len=9, line_score=0.641, ratio_lines=0.480, final_score=0.641
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.454
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.531
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.516
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.565
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=11, match_len=9, line_score=0.220, ratio_lines=0.200, final_score=0.220
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=12, match_len=9, line_score=0.328, ratio_lines=0.286, final_score=0.328
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.603
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.583
trace:         score_window: window_len=13, match_len=9, line_score=0.435, ratio_lines=0.364, final_score=0.435
trace:         score_window: window_len=14, match_len=9, line_score=0.540, ratio_lines=0.435, final_score=0.540
trace:         score_window: window_len=15, match_len=9, line_score=0.644, ratio_lines=0.500, final_score=0.644
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.554
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.489
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.548
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=10, match_len=9, line_score=0.221, ratio_lines=0.211, final_score=0.229
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.564
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=11, match_len=9, line_score=0.330, ratio_lines=0.300, final_score=0.330
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.558
trace:         score_window: window_len=12, match_len=9, line_score=0.437, ratio_lines=0.381, final_score=0.437
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.481
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.603
trace:         score_window: window_len=13, match_len=9, line_score=0.543, ratio_lines=0.455, final_score=0.543
trace:         score_window: window_len=14, match_len=9, line_score=0.648, ratio_lines=0.522, final_score=0.648
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.647
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=9, match_len=9, line_score=0.222, ratio_lines=0.222, final_score=0.243
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.597
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.568
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=10, match_len=9, line_score=0.331, ratio_lines=0.316, final_score=0.341
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=11, match_len=9, line_score=0.440, ratio_lines=0.400, final_score=0.440
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=12, match_len=9, line_score=0.546, ratio_lines=0.476, final_score=0.546
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.592
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.591
trace:         score_window: window_len=13, match_len=9, line_score=0.652, ratio_lines=0.545, final_score=0.652
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=9, match_len=9, line_score=0.333, ratio_lines=0.333, final_score=0.363
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=8, match_len=9, line_score=0.235, ratio_lines=0.235, final_score=0.259
trace:         score_window: window_len=10, match_len=9, line_score=0.442, ratio_lines=0.421, final_score=0.454
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.507
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.591
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=11, match_len=9, line_score=0.549, ratio_lines=0.500, final_score=0.554
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.454
trace:         score_window: window_len=12, match_len=9, line_score=0.656, ratio_lines=0.571, final_score=0.656
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.454
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.539
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=9, match_len=9, line_score=0.444, ratio_lines=0.444, final_score=0.479
trace:         score_window: window_len=8, match_len=9, line_score=0.353, ratio_lines=0.353, final_score=0.385
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.511
trace:         score_window: window_len=10, match_len=9, line_score=0.552, ratio_lines=0.526, final_score=0.584
trace:         score_window: window_len=7, match_len=9, line_score=0.250, ratio_lines=0.250, final_score=0.275
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=11, match_len=9, line_score=0.659, ratio_lines=0.600, final_score=0.662
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.548
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.454
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.494
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.541
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=9, match_len=9, line_score=0.556, ratio_lines=0.556, final_score=0.620
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.573
trace:         score_window: window_len=8, match_len=9, line_score=0.471, ratio_lines=0.471, final_score=0.512
trace:         score_window: window_len=10, match_len=9, line_score=0.663, ratio_lines=0.632, final_score=0.701
trace:         score_window: window_len=7, match_len=9, line_score=0.375, ratio_lines=0.375, final_score=0.412
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=6, match_len=9, line_score=0.267, ratio_lines=0.267, final_score=0.297
trace:         score_window: window_len=5, match_len=9, line_score=0.143, ratio_lines=0.143, final_score=0.520
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=9, match_len=9, line_score=0.667, ratio_lines=0.667, final_score=0.700
trace:         score_window: window_len=8, match_len=9, line_score=0.588, ratio_lines=0.588, final_score=0.664
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.458
trace:         score_window: window_len=7, match_len=9, line_score=0.500, ratio_lines=0.500, final_score=0.551
trace:         score_window: window_len=6, match_len=9, line_score=0.400, ratio_lines=0.400, final_score=0.447
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=5, match_len=9, line_score=0.286, ratio_lines=0.286, final_score=0.323
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.454
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=7, match_len=9, line_score=0.625, ratio_lines=0.625, final_score=0.708
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=6, match_len=9, line_score=0.533, ratio_lines=0.533, final_score=0.591
trace:         score_window: window_len=5, match_len=9, line_score=0.429, ratio_lines=0.429, final_score=0.481
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.573
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=6, match_len=9, line_score=0.667, ratio_lines=0.667, final_score=0.708
trace:         score_window: window_len=5, match_len=9, line_score=0.571, ratio_lines=0.571, final_score=0.634
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=28, match_len=9, line_score=0.696, ratio_lines=0.378, final_score=0.696
trace:         score_window: window_len=29, match_len=9, line_score=0.691, ratio_lines=0.368, final_score=0.691
trace:         score_window: window_len=30, match_len=9, line_score=0.687, ratio_lines=0.359, final_score=0.687
trace:         score_window: window_len=31, match_len=9, line_score=0.683, ratio_lines=0.350, final_score=0.683
trace:         score_window: window_len=32, match_len=9, line_score=0.678, ratio_lines=0.341, final_score=0.678
trace:         score_window: window_len=33, match_len=9, line_score=0.674, ratio_lines=0.333, final_score=0.674
trace:         score_window: window_len=9, match_len=9, line_score=0.667, ratio_lines=0.667, final_score=0.729
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.609
trace:         score_window: window_len=10, match_len=9, line_score=0.663, ratio_lines=0.632, final_score=0.713
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.551
trace:         score_window: window_len=11, match_len=9, line_score=0.659, ratio_lines=0.600, final_score=0.670
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.494
trace:         score_window: window_len=12, match_len=9, line_score=0.656, ratio_lines=0.571, final_score=0.656
trace:         score_window: window_len=13, match_len=9, line_score=0.652, ratio_lines=0.545, final_score=0.652
trace:         score_window: window_len=14, match_len=9, line_score=0.648, ratio_lines=0.522, final_score=0.648
trace:         score_window: window_len=15, match_len=9, line_score=0.644, ratio_lines=0.500, final_score=0.644
trace:         score_window: window_len=16, match_len=9, line_score=0.641, ratio_lines=0.480, final_score=0.641
trace:         score_window: window_len=17, match_len=9, line_score=0.637, ratio_lines=0.462, final_score=0.637
trace:         score_window: window_len=18, match_len=9, line_score=0.633, ratio_lines=0.444, final_score=0.633
trace:         score_window: window_len=19, match_len=9, line_score=0.630, ratio_lines=0.429, final_score=0.630
trace:         score_window: window_len=20, match_len=9, line_score=0.626, ratio_lines=0.414, final_score=0.626
trace:         score_window: window_len=21, match_len=9, line_score=0.622, ratio_lines=0.400, final_score=0.622
trace:         score_window: window_len=22, match_len=9, line_score=0.619, ratio_lines=0.387, final_score=0.619
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=23, match_len=9, line_score=0.615, ratio_lines=0.375, final_score=0.615
trace:         score_window: window_len=24, match_len=9, line_score=0.611, ratio_lines=0.364, final_score=0.611
trace:         score_window: window_len=25, match_len=9, line_score=0.607, ratio_lines=0.353, final_score=0.607
trace:         score_window: window_len=26, match_len=9, line_score=0.604, ratio_lines=0.343, final_score=0.604
trace:         score_window: window_len=27, match_len=9, line_score=0.600, ratio_lines=0.333, final_score=0.600
trace:         score_window: window_len=28, match_len=9, line_score=0.596, ratio_lines=0.324, final_score=0.596
trace:         score_window: window_len=29, match_len=9, line_score=0.593, ratio_lines=0.316, final_score=0.593
trace:         score_window: window_len=30, match_len=9, line_score=0.589, ratio_lines=0.308, final_score=0.589
trace:         score_window: window_len=31, match_len=9, line_score=0.585, ratio_lines=0.300, final_score=0.585
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=32, match_len=9, line_score=0.581, ratio_lines=0.293, final_score=0.581
trace:         score_window: window_len=33, match_len=9, line_score=0.578, ratio_lines=0.286, final_score=0.578
trace:         score_window: window_len=9, match_len=9, line_score=0.556, ratio_lines=0.556, final_score=0.631
trace:         score_window: window_len=8, match_len=9, line_score=0.588, ratio_lines=0.588, final_score=0.669
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.506
trace:         score_window: window_len=10, match_len=9, line_score=0.552, ratio_lines=0.526, final_score=0.590
trace:         score_window: window_len=7, match_len=9, line_score=0.625, ratio_lines=0.625, final_score=0.709
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.615
trace:         score_window: window_len=11, match_len=9, line_score=0.549, ratio_lines=0.500, final_score=0.555
trace:         score_window: window_len=6, match_len=9, line_score=0.667, ratio_lines=0.667, final_score=0.725
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.658
trace:         score_window: window_len=12, match_len=9, line_score=0.546, ratio_lines=0.476, final_score=0.546
trace:         score_window: window_len=13, match_len=9, line_score=0.543, ratio_lines=0.455, final_score=0.543
trace:         score_window: window_len=14, match_len=9, line_score=0.540, ratio_lines=0.435, final_score=0.540
trace:         score_window: window_len=15, match_len=9, line_score=0.537, ratio_lines=0.417, final_score=0.537
trace:         score_window: window_len=16, match_len=9, line_score=0.534, ratio_lines=0.400, final_score=0.534
trace:         score_window: window_len=17, match_len=9, line_score=0.531, ratio_lines=0.385, final_score=0.531
trace:         score_window: window_len=18, match_len=9, line_score=0.528, ratio_lines=0.370, final_score=0.528
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.599
trace:         score_window: window_len=19, match_len=9, line_score=0.525, ratio_lines=0.357, final_score=0.525
trace:         score_window: window_len=20, match_len=9, line_score=0.522, ratio_lines=0.345, final_score=0.522
trace:         score_window: window_len=21, match_len=9, line_score=0.519, ratio_lines=0.333, final_score=0.519
trace:         score_window: window_len=22, match_len=9, line_score=0.515, ratio_lines=0.323, final_score=0.515
trace:         score_window: window_len=23, match_len=9, line_score=0.512, ratio_lines=0.312, final_score=0.512
trace:         score_window: window_len=24, match_len=9, line_score=0.509, ratio_lines=0.303, final_score=0.509
trace:         score_window: window_len=25, match_len=9, line_score=0.506, ratio_lines=0.294, final_score=0.506
trace:         score_window: window_len=26, match_len=9, line_score=0.503, ratio_lines=0.286, final_score=0.503
trace:         score_window: window_len=27, match_len=9, line_score=0.500, ratio_lines=0.278, final_score=0.500
trace:         score_window: window_len=28, match_len=9, line_score=0.497, ratio_lines=0.270, final_score=0.497
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=29, match_len=9, line_score=0.494, ratio_lines=0.263, final_score=0.494
trace:         score_window: window_len=30, match_len=9, line_score=0.491, ratio_lines=0.256, final_score=0.491
trace:         score_window: window_len=31, match_len=9, line_score=0.488, ratio_lines=0.250, final_score=0.488
trace:         score_window: window_len=32, match_len=9, line_score=0.485, ratio_lines=0.244, final_score=0.485
trace:         score_window: window_len=33, match_len=9, line_score=0.481, ratio_lines=0.238, final_score=0.481
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=9, match_len=9, line_score=0.444, ratio_lines=0.444, final_score=0.506
trace:         score_window: window_len=8, match_len=9, line_score=0.471, ratio_lines=0.471, final_score=0.543
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=10, match_len=9, line_score=0.442, ratio_lines=0.421, final_score=0.474
trace:         score_window: window_len=7, match_len=9, line_score=0.500, ratio_lines=0.500, final_score=0.578
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=11, match_len=9, line_score=0.440, ratio_lines=0.400, final_score=0.450
trace:         score_window: window_len=6, match_len=9, line_score=0.533, ratio_lines=0.533, final_score=0.615
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.480
trace:         score_window: window_len=12, match_len=9, line_score=0.437, ratio_lines=0.381, final_score=0.437
trace:         score_window: window_len=5, match_len=9, line_score=0.571, ratio_lines=0.571, final_score=0.658
trace:         score_window: window_len=13, match_len=9, line_score=0.435, ratio_lines=0.364, final_score=0.435
trace:         score_window: window_len=14, match_len=9, line_score=0.432, ratio_lines=0.348, final_score=0.432
trace:         score_window: window_len=15, match_len=9, line_score=0.430, ratio_lines=0.333, final_score=0.430
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.559
trace:         score_window: window_len=16, match_len=9, line_score=0.427, ratio_lines=0.320, final_score=0.427
trace:         score_window: window_len=17, match_len=9, line_score=0.425, ratio_lines=0.308, final_score=0.425
trace:         score_window: window_len=18, match_len=9, line_score=0.422, ratio_lines=0.296, final_score=0.422
trace:         score_window: window_len=19, match_len=9, line_score=0.420, ratio_lines=0.286, final_score=0.420
trace:         score_window: window_len=20, match_len=9, line_score=0.417, ratio_lines=0.276, final_score=0.417
trace:         score_window: window_len=21, match_len=9, line_score=0.415, ratio_lines=0.267, final_score=0.415
trace:         score_window: window_len=22, match_len=9, line_score=0.412, ratio_lines=0.258, final_score=0.412
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.601
trace:         score_window: window_len=23, match_len=9, line_score=0.410, ratio_lines=0.250, final_score=0.410
trace:         score_window: window_len=24, match_len=9, line_score=0.407, ratio_lines=0.242, final_score=0.407
trace:         score_window: window_len=25, match_len=9, line_score=0.405, ratio_lines=0.235, final_score=0.405
trace:         score_window: window_len=26, match_len=9, line_score=0.402, ratio_lines=0.229, final_score=0.402
trace:         score_window: window_len=27, match_len=9, line_score=0.400, ratio_lines=0.222, final_score=0.400
trace:         score_window: window_len=28, match_len=9, line_score=0.398, ratio_lines=0.216, final_score=0.398
trace:         score_window: window_len=29, match_len=9, line_score=0.395, ratio_lines=0.211, final_score=0.395
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.519
trace:         score_window: window_len=9, match_len=9, line_score=0.333, ratio_lines=0.333, final_score=0.385
trace:         score_window: window_len=8, match_len=9, line_score=0.353, ratio_lines=0.353, final_score=0.412
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.561
trace:         score_window: window_len=10, match_len=9, line_score=0.331, ratio_lines=0.316, final_score=0.365
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.519
trace:         score_window: window_len=7, match_len=9, line_score=0.375, ratio_lines=0.375, final_score=0.444
trace:         score_window: window_len=11, match_len=9, line_score=0.330, ratio_lines=0.300, final_score=0.346
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=6, match_len=9, line_score=0.400, ratio_lines=0.400, final_score=0.475
trace:         score_window: window_len=12, match_len=9, line_score=0.328, ratio_lines=0.286, final_score=0.330
trace:         score_window: window_len=5, match_len=9, line_score=0.429, ratio_lines=0.429, final_score=0.509
trace:         score_window: window_len=13, match_len=9, line_score=0.326, ratio_lines=0.273, final_score=0.326
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.486
trace:         score_window: window_len=14, match_len=9, line_score=0.324, ratio_lines=0.261, final_score=0.324
trace:         score_window: window_len=15, match_len=9, line_score=0.322, ratio_lines=0.250, final_score=0.322
trace:         score_window: window_len=16, match_len=9, line_score=0.320, ratio_lines=0.240, final_score=0.320
trace:         score_window: window_len=17, match_len=9, line_score=0.319, ratio_lines=0.231, final_score=0.319
trace:         score_window: window_len=18, match_len=9, line_score=0.317, ratio_lines=0.222, final_score=0.317
trace:         score_window: window_len=19, match_len=9, line_score=0.315, ratio_lines=0.214, final_score=0.315
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=9, match_len=9, line_score=0.222, ratio_lines=0.222, final_score=0.252
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.577
trace:         score_window: window_len=8, match_len=9, line_score=0.235, ratio_lines=0.235, final_score=0.268
trace:         score_window: window_len=10, match_len=9, line_score=0.221, ratio_lines=0.211, final_score=0.238
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.551
trace:         score_window: window_len=7, match_len=9, line_score=0.250, ratio_lines=0.250, final_score=0.287
trace:         score_window: window_len=11, match_len=9, line_score=0.220, ratio_lines=0.200, final_score=0.225
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.551
trace:         score_window: window_len=6, match_len=9, line_score=0.267, ratio_lines=0.267, final_score=0.307
trace:         score_window: window_len=12, match_len=9, line_score=0.219, ratio_lines=0.190, final_score=0.219
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=5, match_len=9, line_score=0.286, ratio_lines=0.286, final_score=0.332
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.598
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.544
trace:         score_window: window_len=9, match_len=9, line_score=0.111, ratio_lines=0.111, final_score=0.552
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.473
trace:         score_window: window_len=8, match_len=9, line_score=0.118, ratio_lines=0.118, final_score=0.668
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.542
trace:         score_window: window_len=10, match_len=9, line_score=0.110, ratio_lines=0.105, final_score=0.607
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.584
trace:         score_window: window_len=7, match_len=9, line_score=0.125, ratio_lines=0.125, final_score=0.619
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.500
trace:         score_window: window_len=11, match_len=9, line_score=0.110, ratio_lines=0.100, final_score=0.575
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.584
trace:         score_window: window_len=6, match_len=9, line_score=0.133, ratio_lines=0.133, final_score=0.565
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.639
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.583
trace:         score_window: window_len=12, match_len=9, line_score=0.109, ratio_lines=0.095, final_score=0.549
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.502
trace:         score_window: window_len=5, match_len=9, line_score=0.143, ratio_lines=0.143, final_score=0.502
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.521
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.622
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.486
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.565
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.534
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.587
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.481
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.689
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.534
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.588
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.560
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.487
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.638
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.582
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.505
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.545
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.497
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.473
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.579
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.518
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.457
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=12, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.444
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.492
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.476
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.646
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.499
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.587
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.488
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.457
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.455
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.443
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.416
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.513
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.458
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.539
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.582
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.441
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.539
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.474
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.440
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.458
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.458
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.483
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.454
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.483
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.444
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.451
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.466
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.423
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.423
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.336
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.399
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.458
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.341
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.555
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.598
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.399
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.288
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.458
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.490
trace:         score_window: window_len=9, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.514
trace:         score_window: window_len=8, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.533
trace:         score_window: window_len=10, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.485
trace:         score_window: window_len=7, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.553
trace:         score_window: window_len=11, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.458
trace:         score_window: window_len=6, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.508
trace:         score_window: window_len=5, match_len=9, line_score=0.000, ratio_lines=0.000, final_score=0.454
debug:       compute_scored_windows (parallel) complete: scored 1479 window(s). Best candidate score=0.875 at line 127 (len=7).
trace:       Top fuzzy match candidates:
trace:         - Index 126, Len 7: Score 0.875 (Ratio 0.875) | Content: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:         - Index 125, Len 8: Score 0.824 (Ratio 0.824) | Content: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:         - Index 126, Len 8: Score 0.824 (Ratio 0.824) | Content: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:         - Index 126, Len 6: Score 0.800 (Ratio 0.800) | Content: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages"]
trace:         - Index 127, Len 6: Score 0.800 (Ratio 0.800) | Content: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:         New best score: 0.541 (ratio 0.541 [l:0.000,w:0.735]) at index 108 (window len 9)
trace:         New best score: 0.574 (ratio 0.574 [l:0.000,w:0.761]) at index 108 (window len 8)
trace:         New best score: 0.611 (ratio 0.611 [l:0.000,w:0.791]) at index 108 (window len 7)
trace:         New best score: 0.681 (ratio 0.681 [l:0.000,w:0.000]) at index 108 (window len 12)
trace:         New best score: 0.690 (ratio 0.690 [l:0.200,w:0.000]) at index 108 (window len 21)
trace:         New best score: 0.709 (ratio 0.709 [l:0.412,w:0.709]) at index 108 (window len 25)
trace:         New best score: 0.713 (ratio 0.713 [l:0.424,w:0.713]) at index 109 (window len 24)
trace:         New best score: 0.717 (ratio 0.717 [l:0.438,w:0.717]) at index 110 (window len 23)
trace:         New best score: 0.722 (ratio 0.722 [l:0.452,w:0.722]) at index 111 (window len 22)
trace:         New best score: 0.726 (ratio 0.726 [l:0.467,w:0.726]) at index 112 (window len 21)
trace:         New best score: 0.730 (ratio 0.730 [l:0.483,w:0.730]) at index 113 (window len 20)
trace:         New best score: 0.735 (ratio 0.735 [l:0.500,w:0.735]) at index 114 (window len 19)
trace:         New best score: 0.739 (ratio 0.739 [l:0.519,w:0.739]) at index 115 (window len 18)
trace:         New best score: 0.743 (ratio 0.743 [l:0.538,w:0.743]) at index 116 (window len 17)
trace:         New best score: 0.748 (ratio 0.748 [l:0.560,w:0.748]) at index 117 (window len 16)
trace:         New best score: 0.752 (ratio 0.752 [l:0.583,w:0.752]) at index 118 (window len 15)
trace:         New best score: 0.756 (ratio 0.756 [l:0.609,w:0.756]) at index 119 (window len 14)
trace:         New best score: 0.760 (ratio 0.760 [l:0.636,w:0.760]) at index 120 (window len 13)
trace:         New best score: 0.765 (ratio 0.765 [l:0.667,w:0.765]) at index 121 (window len 12)
trace:         New best score: 0.769 (ratio 0.769 [l:0.700,w:0.769]) at index 122 (window len 11)
trace:         New best score: 0.773 (ratio 0.773 [l:0.737,w:0.773]) at index 123 (window len 10)
trace:         New best score: 0.778 (ratio 0.778 [l:0.778,w:0.778]) at index 124 (window len 9)
trace:         Tie in score (0.778) and ratio (0.778). Adding candidate: index 125, len 9
trace:         New best score: 0.824 (ratio 0.824 [l:0.824,w:0.824]) at index 125 (window len 8)
trace:         Tie in score (0.824) and ratio (0.824). Adding candidate: index 126, len 8
trace:         New best score: 0.875 (ratio 0.875 [l:0.875,w:0.875]) at index 126 (window len 7)
debug:     Strategy 3 (Fuzzy): 246 window(s) met threshold 0.70
trace:       Top 3 passing candidates: [("0.875", 127, 7), ("0.824", 126, 8), ("0.824", 127, 8)]
debug:     Top fuzzy candidate: start line 127 (len=7, score=0.875)
trace:       Adding candidate location at line 126 (len=8, score=0.824)
trace:       Adding candidate location at line 127 (len=8, score=0.824)
trace:       Adding candidate location at line 127 (len=6, score=0.800)
trace:       Adding candidate location at line 128 (len=6, score=0.800)
trace:       Adding candidate location at line 125 (len=9, score=0.778)
trace:       Adding candidate location at line 126 (len=9, score=0.778)
trace:       Adding candidate location at line 127 (len=9, score=0.778)
trace:       Adding candidate location at line 124 (len=10, score=0.773)
trace:       Adding candidate location at line 125 (len=10, score=0.773)
trace:       Adding candidate location at line 126 (len=10, score=0.773)
trace:       Adding candidate location at line 127 (len=10, score=0.773)
trace:       Adding candidate location at line 123 (len=11, score=0.769)
trace:       Adding candidate location at line 124 (len=11, score=0.769)
trace:       Adding candidate location at line 125 (len=11, score=0.769)
trace:       Adding candidate location at line 126 (len=11, score=0.769)
trace:       Adding candidate location at line 122 (len=12, score=0.765)
trace:       Adding candidate location at line 123 (len=12, score=0.765)
trace:       Adding candidate location at line 124 (len=12, score=0.765)
trace:       Adding candidate location at line 125 (len=12, score=0.765)
trace:       Reached maximum candidate limit (20), stopping candidate collection
debug:     Strategy 3 (Fuzzy): selected 20 candidate location(s)
trace:   Pruned candidates by min_span 5: 20 -> 20 candidate(s)
trace: DefaultHunkFinder::find_candidate_locations: returning 20 candidate(s)
debug:   Found 20 candidate location(s) for hunk. Testing sequentially...
trace:   Evaluating candidate 1/20 at location HunkLocation { start_index: 126, length: 7 } (match_type: Fuzzy { score: 0.875 })
debug:   Found location HunkLocation { start_index: 126, length: 7 } with match type Fuzzy { score: 0.875 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 127 (length 7), match_type=Fuzzy { score: 0.875 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=126, len=7
trace:       File content in matched range (7 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.875
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 1/20 at HunkLocation { start_index: 126, length: 7 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 2/20 at location HunkLocation { start_index: 125, length: 8 } (match_type: Fuzzy { score: 0.8235294222831726 })
debug:   Found location HunkLocation { start_index: 125, length: 8 } with match type Fuzzy { score: 0.8235294222831726 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 126 (length 8), match_type=Fuzzy { score: 0.8235294222831726 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=125, len=8
trace:       File content in matched range (8 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.824
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 2/20 at HunkLocation { start_index: 125, length: 8 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 3/20 at location HunkLocation { start_index: 126, length: 8 } (match_type: Fuzzy { score: 0.8235294222831726 })
debug:   Found location HunkLocation { start_index: 126, length: 8 } with match type Fuzzy { score: 0.8235294222831726 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 127 (length 8), match_type=Fuzzy { score: 0.8235294222831726 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=126, len=8
trace:       File content in matched range (8 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.824
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 7..8 (len=1)
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
debug:   Candidate 3/20 at HunkLocation { start_index: 126, length: 8 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 4/20 at location HunkLocation { start_index: 126, length: 6 } (match_type: Fuzzy { score: 0.800000011920929 })
debug:   Found location HunkLocation { start_index: 126, length: 6 } with match type Fuzzy { score: 0.800000011920929 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 127 (length 6), match_type=Fuzzy { score: 0.800000011920929 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=126, len=6
trace:       File content in matched range (6 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.800
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:       DiffOp::Delete: 3 line(s) missing from target file (hunk old_idx=6)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 4/20 at HunkLocation { start_index: 126, length: 6 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 5/20 at location HunkLocation { start_index: 127, length: 6 } (match_type: Fuzzy { score: 0.800000011920929 })
debug:   Found location HunkLocation { start_index: 127, length: 6 } with match type Fuzzy { score: 0.800000011920929 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 128 (length 6), match_type=Fuzzy { score: 0.800000011920929 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=127, len=6
trace:       File content in matched range (6 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.800
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Delete: 1 line(s) missing from target file (hunk old_idx=0)
trace:         Skipping stale context line missing in target: "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr"
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=1, file new_idx=0)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 5/20 at HunkLocation { start_index: 127, length: 6 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 6/20 at location HunkLocation { start_index: 124, length: 9 } (match_type: Fuzzy { score: 0.7777777910232544 })
debug:   Found location HunkLocation { start_index: 124, length: 9 } with match type Fuzzy { score: 0.7777777910232544 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 125 (length 9), match_type=Fuzzy { score: 0.7777777910232544 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=124, len=9
trace:       File content in matched range (9 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.778
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 6/20 at HunkLocation { start_index: 124, length: 9 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 7/20 at location HunkLocation { start_index: 125, length: 9 } (match_type: Fuzzy { score: 0.7777777910232544 })
debug:   Found location HunkLocation { start_index: 125, length: 9 } with match type Fuzzy { score: 0.7777777910232544 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 126 (length 9), match_type=Fuzzy { score: 0.7777777910232544 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=125, len=9
trace:       File content in matched range (9 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.778
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 8..9 (len=1)
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
debug:   Candidate 7/20 at HunkLocation { start_index: 125, length: 9 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 8/20 at location HunkLocation { start_index: 126, length: 9 } (match_type: Fuzzy { score: 0.7777777910232544 })
debug:   Found location HunkLocation { start_index: 126, length: 9 } with match type Fuzzy { score: 0.7777777910232544 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 127 (length 9), match_type=Fuzzy { score: 0.7777777910232544 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=126, len=9
trace:       File content in matched range (9 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.778
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 7..9 (len=2)
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace:         1-to-1 replacement line validation [line 7]: is_removal=true, word_sim=0.000, char_sim=0.000
warning:     Fuzzy match rejected: Removal line "- " differs from target line "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data" (sim_words=0.000, sim_chars=0.000, required=0.500).
debug:   Candidate 8/20 at HunkLocation { start_index: 126, length: 9 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 9/20 at location HunkLocation { start_index: 123, length: 10 } (match_type: Fuzzy { score: 0.7734567802445388 })
debug:   Found location HunkLocation { start_index: 123, length: 10 } with match type Fuzzy { score: 0.7734567802445388 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 124 (length 10), match_type=Fuzzy { score: 0.7734567802445388 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=123, len=10
trace:       File content in matched range (10 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.737
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 3 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=3)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 9/20 at HunkLocation { start_index: 123, length: 10 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 10/20 at location HunkLocation { start_index: 124, length: 10 } (match_type: Fuzzy { score: 0.7734567802445388 })
debug:   Found location HunkLocation { start_index: 124, length: 10 } with match type Fuzzy { score: 0.7734567802445388 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 125 (length 10), match_type=Fuzzy { score: 0.7734567802445388 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=124, len=10
trace:       File content in matched range (10 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.737
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 9..10 (len=1)
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
debug:   Candidate 10/20 at HunkLocation { start_index: 124, length: 10 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 11/20 at location HunkLocation { start_index: 125, length: 10 } (match_type: Fuzzy { score: 0.7734567802445388 })
debug:   Found location HunkLocation { start_index: 125, length: 10 } with match type Fuzzy { score: 0.7734567802445388 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 126 (length 10), match_type=Fuzzy { score: 0.7734567802445388 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=125, len=10
trace:       File content in matched range (10 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.737
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 8..10 (len=2)
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace:         1-to-1 replacement line validation [line 7]: is_removal=true, word_sim=0.000, char_sim=0.000
warning:     Fuzzy match rejected: Removal line "- " differs from target line "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data" (sim_words=0.000, sim_chars=0.000, required=0.500).
debug:   Candidate 11/20 at HunkLocation { start_index: 125, length: 10 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 12/20 at location HunkLocation { start_index: 126, length: 10 } (match_type: Fuzzy { score: 0.7734567802445388 })
debug:   Found location HunkLocation { start_index: 126, length: 10 } with match type Fuzzy { score: 0.7734567802445388 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 127 (length 10), match_type=Fuzzy { score: 0.7734567802445388 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=126, len=10
trace:       File content in matched range (10 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.737
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 7..10 (len=3)
trace:         Multi-line replacement (hunk_len=2, target_len=3). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 3 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:   find_statement_match_in_block: comparing target line 2 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:   find_statement_match_in_block: comparing target line 3 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
debug:   Candidate 12/20 at HunkLocation { start_index: 126, length: 10 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 13/20 at location HunkLocation { start_index: 122, length: 11 } (match_type: Fuzzy { score: 0.7691357893708312 })
debug:   Found location HunkLocation { start_index: 122, length: 11 } with match type Fuzzy { score: 0.7691357893708312 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 123 (length 11), match_type=Fuzzy { score: 0.7691357893708312 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=122, len=11
trace:       File content in matched range (11 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.700
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 4 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=4)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 13/20 at HunkLocation { start_index: 122, length: 11 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 14/20 at location HunkLocation { start_index: 123, length: 11 } (match_type: Fuzzy { score: 0.7691357893708312 })
debug:   Found location HunkLocation { start_index: 123, length: 11 } with match type Fuzzy { score: 0.7691357893708312 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 124 (length 11), match_type=Fuzzy { score: 0.7691357893708312 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=123, len=11
trace:       File content in matched range (11 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.700
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 3 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=3)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 10..11 (len=1)
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
debug:   Candidate 14/20 at HunkLocation { start_index: 123, length: 11 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 15/20 at location HunkLocation { start_index: 124, length: 11 } (match_type: Fuzzy { score: 0.7691357893708312 })
debug:   Found location HunkLocation { start_index: 124, length: 11 } with match type Fuzzy { score: 0.7691357893708312 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 125 (length 11), match_type=Fuzzy { score: 0.7691357893708312 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=124, len=11
trace:       File content in matched range (11 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.700
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 9..11 (len=2)
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace:         1-to-1 replacement line validation [line 7]: is_removal=true, word_sim=0.000, char_sim=0.000
warning:     Fuzzy match rejected: Removal line "- " differs from target line "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data" (sim_words=0.000, sim_chars=0.000, required=0.500).
debug:   Candidate 15/20 at HunkLocation { start_index: 124, length: 11 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 16/20 at location HunkLocation { start_index: 125, length: 11 } (match_type: Fuzzy { score: 0.7691357893708312 })
debug:   Found location HunkLocation { start_index: 125, length: 11 } with match type Fuzzy { score: 0.7691357893708312 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 126 (length 11), match_type=Fuzzy { score: 0.7691357893708312 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=125, len=11
trace:       File content in matched range (11 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.700
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 8..11 (len=3)
trace:         Multi-line replacement (hunk_len=2, target_len=3). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 3 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:   find_statement_match_in_block: comparing target line 2 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:   find_statement_match_in_block: comparing target line 3 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
debug:   Candidate 16/20 at HunkLocation { start_index: 125, length: 11 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 17/20 at location HunkLocation { start_index: 121, length: 12 } (match_type: Fuzzy { score: 0.7648148376080725 })
debug:   Found location HunkLocation { start_index: 121, length: 12 } with match type Fuzzy { score: 0.7648148376080725 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 122 (length 12), match_type=Fuzzy { score: 0.7648148376080725 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += smp_call_function", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=121, len=12
trace:       File content in matched range (12 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += smp_call_function", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.667
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 5 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += smp_call_function'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=5)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
debug:   Candidate 17/20 at HunkLocation { start_index: 121, length: 12 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 18/20 at location HunkLocation { start_index: 122, length: 12 } (match_type: Fuzzy { score: 0.7648148376080725 })
debug:   Found location HunkLocation { start_index: 122, length: 12 } with match type Fuzzy { score: 0.7648148376080725 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 123 (length 12), match_type=Fuzzy { score: 0.7648148376080725 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=122, len=12
trace:       File content in matched range (12 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.667
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 4 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=4)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 11..12 (len=1)
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
debug:   Candidate 18/20 at HunkLocation { start_index: 122, length: 12 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 19/20 at location HunkLocation { start_index: 123, length: 12 } (match_type: Fuzzy { score: 0.7648148376080725 })
debug:   Found location HunkLocation { start_index: 123, length: 12 } with match type Fuzzy { score: 0.7648148376080725 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 124 (length 12), match_type=Fuzzy { score: 0.7648148376080725 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=123, len=12
trace:       File content in matched range (12 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.667
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 3 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=3)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 10..12 (len=2)
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace:         1-to-1 replacement line validation [line 7]: is_removal=true, word_sim=0.000, char_sim=0.000
warning:     Fuzzy match rejected: Removal line "- " differs from target line "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data" (sim_words=0.000, sim_chars=0.000, required=0.500).
debug:   Candidate 19/20 at HunkLocation { start_index: 123, length: 12 } failed with ContextNotFound. Backtracking...
trace:   Evaluating candidate 20/20 at location HunkLocation { start_index: 124, length: 12 } (match_type: Fuzzy { score: 0.7648148376080725 })
debug:   Found location HunkLocation { start_index: 124, length: 12 } with match type Fuzzy { score: 0.7648148376080725 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 125 (length 12), match_type=Fuzzy { score: 0.7648148376080725 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=124, len=12
trace:       File content in matched range (12 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.667
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 9..12 (len=3)
trace:         Multi-line replacement (hunk_len=2, target_len=3). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 3 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:   find_statement_match_in_block: comparing target line 2 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:   find_statement_match_in_block: comparing target line 3 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
debug:   Candidate 20/20 at HunkLocation { start_index: 124, length: 12 } failed with ContextNotFound. Backtracking...
debug:   Strict application failed for all 20 candidate(s). Retrying with fallback context reconciliation...
trace:   Evaluating candidate 1/20 with lenient reconciliation at location HunkLocation { start_index: 126, length: 7 }
debug:   Found location HunkLocation { start_index: 126, length: 7 } with match type Fuzzy { score: 0.875 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 127 (length 7), match_type=Fuzzy { score: 0.875 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=126, len=7
trace:       File content in matched range (7 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.875
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 2/20 with lenient reconciliation at location HunkLocation { start_index: 125, length: 8 }
debug:   Found location HunkLocation { start_index: 125, length: 8 } with match type Fuzzy { score: 0.8235294222831726 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 126 (length 8), match_type=Fuzzy { score: 0.8235294222831726 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=125, len=8
trace:       File content in matched range (8 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.824
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 3/20 with lenient reconciliation at location HunkLocation { start_index: 126, length: 8 }
debug:   Found location HunkLocation { start_index: 126, length: 8 } with match type Fuzzy { score: 0.8235294222831726 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 127 (length 8), match_type=Fuzzy { score: 0.8235294222831726 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=126, len=8
trace:       File content in matched range (8 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.824
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 7..8 (len=1)
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
trace:   Evaluating candidate 4/20 with lenient reconciliation at location HunkLocation { start_index: 126, length: 6 }
debug:   Found location HunkLocation { start_index: 126, length: 6 } with match type Fuzzy { score: 0.800000011920929 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 127 (length 6), match_type=Fuzzy { score: 0.800000011920929 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=126, len=6
trace:       File content in matched range (6 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.800
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:       DiffOp::Delete: 3 line(s) missing from target file (hunk old_idx=6)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 5/20 with lenient reconciliation at location HunkLocation { start_index: 127, length: 6 }
debug:   Found location HunkLocation { start_index: 127, length: 6 } with match type Fuzzy { score: 0.800000011920929 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 128 (length 6), match_type=Fuzzy { score: 0.800000011920929 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=127, len=6
trace:       File content in matched range (6 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.800
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Delete: 1 line(s) missing from target file (hunk old_idx=0)
trace:         Skipping stale context line missing in target: "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr"
trace:       DiffOp::Equal: 6 line(s) aligned (hunk old_idx=1, file new_idx=0)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 6/20 with lenient reconciliation at location HunkLocation { start_index: 124, length: 9 }
debug:   Found location HunkLocation { start_index: 124, length: 9 } with match type Fuzzy { score: 0.7777777910232544 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 125 (length 9), match_type=Fuzzy { score: 0.7777777910232544 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=124, len=9
trace:       File content in matched range (9 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.778
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 7/20 with lenient reconciliation at location HunkLocation { start_index: 125, length: 9 }
debug:   Found location HunkLocation { start_index: 125, length: 9 } with match type Fuzzy { score: 0.7777777910232544 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 126 (length 9), match_type=Fuzzy { score: 0.7777777910232544 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=125, len=9
trace:       File content in matched range (9 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.778
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 8..9 (len=1)
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
trace:   Evaluating candidate 8/20 with lenient reconciliation at location HunkLocation { start_index: 126, length: 9 }
debug:   Found location HunkLocation { start_index: 126, length: 9 } with match type Fuzzy { score: 0.7777777910232544 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 127 (length 9), match_type=Fuzzy { score: 0.7777777910232544 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=126, len=9
trace:       File content in matched range (9 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data'
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.778
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 7..9 (len=2)
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace:         1-to-1 replacement line validation [line 7]: is_removal=true, word_sim=0.000, char_sim=0.000
trace: normalize_line_delimiters: '-' -> '-'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'
warning:     Fuzzy match rejected: Removal line "- " differs from target line "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data" (sim_words=0.000, sim_chars=0.000, required=0.350).
trace:   Evaluating candidate 9/20 with lenient reconciliation at location HunkLocation { start_index: 123, length: 10 }
debug:   Found location HunkLocation { start_index: 123, length: 10 } with match type Fuzzy { score: 0.7734567802445388 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 124 (length 10), match_type=Fuzzy { score: 0.7734567802445388 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=123, len=10
trace:       File content in matched range (10 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.737
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 3 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=3)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 10/20 with lenient reconciliation at location HunkLocation { start_index: 124, length: 10 }
debug:   Found location HunkLocation { start_index: 124, length: 10 } with match type Fuzzy { score: 0.7734567802445388 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 125 (length 10), match_type=Fuzzy { score: 0.7734567802445388 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=124, len=10
trace:       File content in matched range (10 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.737
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 9..10 (len=1)
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
trace:   Evaluating candidate 11/20 with lenient reconciliation at location HunkLocation { start_index: 125, length: 10 }
debug:   Found location HunkLocation { start_index: 125, length: 10 } with match type Fuzzy { score: 0.7734567802445388 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 126 (length 10), match_type=Fuzzy { score: 0.7734567802445388 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=125, len=10
trace:       File content in matched range (10 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.737
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 8..10 (len=2)
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace:         1-to-1 replacement line validation [line 7]: is_removal=true, word_sim=0.000, char_sim=0.000
trace: normalize_line_delimiters: '-' -> '-'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'
warning:     Fuzzy match rejected: Removal line "- " differs from target line "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data" (sim_words=0.000, sim_chars=0.000, required=0.350).
trace:   Evaluating candidate 12/20 with lenient reconciliation at location HunkLocation { start_index: 126, length: 10 }
debug:   Found location HunkLocation { start_index: 126, length: 10 } with match type Fuzzy { score: 0.7734567802445388 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 127 (length 10), match_type=Fuzzy { score: 0.7734567802445388 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=126, len=10
trace:       File content in matched range (10 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA'
trace:       Computed diff between match block and file slice: 2 operation(s), similarity ratio=0.737
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=0)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 7..10 (len=3)
trace:         Multi-line replacement (hunk_len=2, target_len=3). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 3 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:   find_statement_match_in_block: comparing target line 2 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:   find_statement_match_in_block: comparing target line 3 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
trace:   Evaluating candidate 13/20 with lenient reconciliation at location HunkLocation { start_index: 122, length: 11 }
debug:   Found location HunkLocation { start_index: 122, length: 11 } with match type Fuzzy { score: 0.7691357893708312 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 123 (length 11), match_type=Fuzzy { score: 0.7691357893708312 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=122, len=11
trace:       File content in matched range (11 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.700
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 4 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=4)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 14/20 with lenient reconciliation at location HunkLocation { start_index: 123, length: 11 }
debug:   Found location HunkLocation { start_index: 123, length: 11 } with match type Fuzzy { score: 0.7691357893708312 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 124 (length 11), match_type=Fuzzy { score: 0.7691357893708312 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=123, len=11
trace:       File content in matched range (11 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.700
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 3 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=3)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 10..11 (len=1)
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
trace:   Evaluating candidate 15/20 with lenient reconciliation at location HunkLocation { start_index: 124, length: 11 }
debug:   Found location HunkLocation { start_index: 124, length: 11 } with match type Fuzzy { score: 0.7691357893708312 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 125 (length 11), match_type=Fuzzy { score: 0.7691357893708312 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=124, len=11
trace:       File content in matched range (11 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.700
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 9..11 (len=2)
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace:         1-to-1 replacement line validation [line 7]: is_removal=true, word_sim=0.000, char_sim=0.000
trace: normalize_line_delimiters: '-' -> '-'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'
warning:     Fuzzy match rejected: Removal line "- " differs from target line "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data" (sim_words=0.000, sim_chars=0.000, required=0.350).
trace:   Evaluating candidate 16/20 with lenient reconciliation at location HunkLocation { start_index: 125, length: 11 }
debug:   Found location HunkLocation { start_index: 125, length: 11 } with match type Fuzzy { score: 0.7691357893708312 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 126 (length 11), match_type=Fuzzy { score: 0.7691357893708312 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=125, len=11
trace:       File content in matched range (11 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.700
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 1 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=1)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 8..11 (len=3)
trace:         Multi-line replacement (hunk_len=2, target_len=3). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 3 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:   find_statement_match_in_block: comparing target line 2 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:   find_statement_match_in_block: comparing target line 3 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
trace:   Evaluating candidate 17/20 with lenient reconciliation at location HunkLocation { start_index: 121, length: 12 }
debug:   Found location HunkLocation { start_index: 121, length: 12 } with match type Fuzzy { score: 0.7648148376080725 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 122 (length 12), match_type=Fuzzy { score: 0.7648148376080725 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += smp_call_function", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=121, len=12
trace:       File content in matched range (12 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += smp_call_function", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += smp_call_function' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += smp_call_function'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.667
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 5 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += smp_call_function'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=5)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Delete: 2 line(s) missing from target file (hunk old_idx=7)
warning:     Fuzzy match rejected: Tail context line(s) missing from target file.
trace:   Evaluating candidate 18/20 with lenient reconciliation at location HunkLocation { start_index: 122, length: 12 }
debug:   Found location HunkLocation { start_index: 122, length: 12 } with match type Fuzzy { score: 0.7648148376080725 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 123 (length 12), match_type=Fuzzy { score: 0.7648148376080725 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=122, len=12
trace:       File content in matched range (12 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.667
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 4 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_evaluate_integer'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=4)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 11..12 (len=1)
trace:         Multi-line replacement (hunk_len=2, target_len=1). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 1 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
trace:   Evaluating candidate 19/20 with lenient reconciliation at location HunkLocation { start_index: 123, length: 12 }
debug:   Found location HunkLocation { start_index: 123, length: 12 } with match type Fuzzy { score: 0.7648148376080725 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 124 (length 12), match_type=Fuzzy { score: 0.7648148376080725 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=123, len=12
trace:       File content in matched range (12 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.667
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 3 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_cache'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=3)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 10..12 (len=2)
trace:         1-to-1 length replacement. Validating similarity of modified lines...
trace:         1-to-1 replacement line validation [line 7]: is_removal=true, word_sim=0.000, char_sim=0.000
trace: normalize_line_delimiters: '-' -> '-'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'
warning:     Fuzzy match rejected: Removal line "- " differs from target line "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data" (sim_words=0.000, sim_chars=0.000, required=0.350).
trace:   Evaluating candidate 20/20 with lenient reconciliation at location HunkLocation { start_index: 124, length: 12 }
debug:   Found location HunkLocation { start_index: 124, length: 12 } with match type Fuzzy { score: 0.7648148376080725 }. Applying changes.
debug:   try_apply_hunk_at_location: target line 125 (length 12), match_type=Fuzzy { score: 0.7648148376080725 }, total target lines=221.
trace: Hunk::get_match_block: extracted 9 match line(s)
trace:     Match block lines: 9 | Total hunk lines: 10
trace:     Target slice to replace: ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA"]
trace:     Ellipsis flags: has_ellipsis=false, is_literal_match=false, is_wildcard_gap_match=false
debug:     Applying hunk via robust reconstruction logic (preserving file context & adjusting indent).
trace:       Fuzzy match location: start=124, len=12
trace:       File content in matched range (12 line(s)): ["NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data", "NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA"]
trace:       Parsed hunk: 9 match line(s), 0 initial addition(s).
trace: Hunk::get_match_block: extracted 9 match line(s)
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: '- ' -> '-'
trace: normalize_line_delimiters: '2.20.1' -> '2.20.1'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data'
trace: normalize_line_delimiters: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA' -> 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA'
trace:       Computed diff between match block and file slice: 3 operation(s), similarity ratio=0.667
trace:       Active baseline indentation: hunk='', target=''
trace:       DiffOp::Insert: preserving 2 local insertion line(s) from target file (new_idx=0)
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += ioremap_wc'
trace:         Preserving inserted line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += acpi_walk_namespace'
trace:       DiffOp::Equal: 7 line(s) aligned (hunk old_idx=0, file new_idx=2)
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table'
trace:         Equal: removing target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Appended 1 addition(s) after line 3
trace:         Equal: applying addition: '#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages'
trace:         Equal: preserving target line: 'NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled'
trace:       DiffOp::Replace: hunk lines 7..9 (len=2) vs file lines 9..12 (len=3)
trace:         Multi-line replacement (hunk_len=2, target_len=3). Searching for statement alignment across line breaks...
trace: find_statement_match_in_block: attempting statement alignment for 2 line(s) against 3 target line(s)
trace:   find_statement_match_in_block: comparing target line 1 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += proc_create_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:   find_statement_match_in_block: comparing target line 2 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += pde_data'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:   find_statement_match_in_block: comparing target line 3 ('NV_CONFTEST_FUNCTION_COMPILE_TESTS += PDE_DATA'): word_ratio=0.000, char_ratio=0.000, combined=0.000
trace:         No single statement alignment found (has_context=true). Using block fallback heuristic.
warning:     Fuzzy match rejected: Tail context is unaligned in replacement block.
warning:   All 20 candidate location(s) exhausted. Hunk application failed with: Context not found
debug:   HunkApplier: hunk 2 application outcome: Failed(ContextNotFound)
  Applying Hunk 2/2...
warning:   Failed to apply Hunk 2. Context not found
debug: HunkApplier::into_content: assembling final content from 221 line(s) (touched_eof=false, patch_ends_with_newline=true, original_ends_with_newline=true)
trace: HunkApplier::into_content: resulting content has 9107 bytes (221 lines, ends_with_newline=true)
  DRY RUN: Evaluated changes for 'nvidia/nvidia.Kbuild' (2 hunks, clean=false)
trace:   Generating diff for dry run...
debug: apply_patches_to_dir: completed 2 patch(es). all_succeeded=true, all_applied_cleanly=false

>>> Operation 1/2

>>> Operation 2/2
error: --- FAILED to apply patch for: nvidia/nvidia.Kbuild
warning:   - Hunk 2 failed: Context not found
warning:     Failed Hunk Content:
warning:        NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_domain_nr
warning:        NV_CONFTEST_FUNCTION_COMPILE_TESTS += dma_mapping_error
warning:        NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_alloc_table
warning:       -NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table
warning:       +#NV_CONFTEST_FUNCTION_COMPILE_TESTS += sg_init_table
warning:        NV_CONFTEST_FUNCTION_COMPILE_TESTS += pci_get_domain_bus_and_slot
warning:        NV_CONFTEST_FUNCTION_COMPILE_TESTS += get_num_physpages
warning:        NV_CONFTEST_FUNCTION_COMPILE_TESTS += efi_enabled
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
