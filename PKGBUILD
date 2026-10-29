# Maintainer: Gyöngyösi Gábor <gabor at gshoots dot hu>
# Contributor: Mark Wagie <mark at manjaro dot org>
# Contributor: Philip Müller <philm[at]manjaro[dot]org>
# Contributor: Thomas Baechler <thomas@archlinux.org>
# Contributor: Sven-Hendrik Haase <svenstaro@gmail.com>
#
# =============================================================================
#  NVIDIA 390xx – Debian patch-sorozat mpatch-csel
#  For Manjaro-awesome-respin
# =============================================================================
#
#  ┌─────────────────────────────────────────────────────────────────────────┐
#  │  MPATCH – HORDOZHATÓ KÉZIKÖNYV A PKGBUILD-BEN                          │
#  │  (Ha elfelejted, itt minden megtalálható. Nem kell GitHub-ot nyitni.)  │
#  └─────────────────────────────────────────────────────────────────────────┘
#
#  MI ÉS MIÉRT
#  -----------
#  Az mpatch egy fuzzy patchelő. Nem sorszám és nem bájt-pontos kontextus
#  alapján illeszt, hanem hasonlósági algoritmussal keresi a patch helyét.
#  Ez akkor hasznos, ha egy Debian patch egy kicsit elavult a forráshoz
#  képest, DE a változtatás lényege még stimmel.
#
#  KOCKÁZAT
#  --------
#  A fuzzy matching rossz helyre is illeszthet. Ezért:
#    - build-hez MINDIG használj --atomic-ot (minden-vagy-semmi)
#    - a --fuzz-factor-t csak indokolt esetben lazítsd
#    - ha egy patch elhasal: először debug, csak utána lazítás
#
#  ---------------------------------------------------------------------------
#  BEVEZETŐ FORMÁTUMOK (amit az mpatch automatikusan felismer)
#  ---------------------------------------------------------------------------
#   1. Unified Diff          – ez a Debian patchek formátuma (--- a/ +++ b/)
#   2. Markdown diff blokk   – ```diff ... ``` (LLM kimenet)
#   3. Aider Search/Replace  – <<<<<<< SEARCH ... ======= ... >>>>>>> REPLACE
#   4. Conflict Markers      – <<<< ==== >>>> (nincs benne fájlútvonal!)
#
#  A Debian patcheink az 1-es típusba esnek. A 4-es típus CLI-ből
#  csak egy "patch_target" nevű fájlt tud patchelni – nekünk nem jó.
#
#  ---------------------------------------------------------------------------
#  FORMÁTUM-LIMITÁCIÓK (ezeket az mpatch NEM tudja alkalmazni)
#  ---------------------------------------------------------------------------
#  Ha a patch az alábbiak bármelyikét tartalmazza, az mpatch NEM
#  próbálkozik fuzzy-val, hanem azonnal leáll (exit 1, semmit nem ír):
#
#    - Git rename/copy:    "rename from" / "copy from"
#    - Git binary patch:   "GIT binary patch"
#    - Symlink / submodule mód (bármi, ami nem 100644 / 100755)
#    - Context diff:       "diff -c"  → regeneráld "diff -u"-val
#
#  ⚠ EZ NEM FUZZ-PROBLÉMA. Ha egy patch elbukik, ELŐSZÖR ezt kell
#  kizárni, mielőtt a fuzz-factort lazítanád. Ha ezek közül van benne,
#  a --fuzz-factor 0.3 sem segít – a patchet ki kell venni, vagy
#  kézzel át kell írni.
#
#  ---------------------------------------------------------------------------
#  PARANCSONKÉNTI OPCIÓK (mind a PKGBUILD _mpatch_opts tömbben)
#  ---------------------------------------------------------------------------
#
#  --fuzz-factor N            Hasonlósági küszöb, 0.0 – 1.0
#     0.0   = fuzzy KIKAPCSOLVA. Az egzakt és a trailing-whitespace-t
#             toleráló match továbbra is működik. NEM bájt-pontos, és
#             NEM viselkedik úgy, mint a GNU patch. Preview: --dry-run.
#     0.5   = laza (kockázatos, csak debug célra)
#     0.7   = DEFAULT (a tool ajánlott értéke)
#     0.9   = nagyon szigorú (kevés eltűréssel)
#     1.0   = gyakorlatilag csak tökéletes egyezés
#
#     MIKOR MELYIK?
#       - Build-hez: 0.7 (default) vagy 0.9 (ha van idő debugolni)
#       - Ha egy patch elhasal 0.7-en: ELŐSZÖR a FORMÁTUM-LIMITÁCIÓK
#         szekciót kell kizárni (fent), csak utána lazíts 0.5-re.
#         Ha 0.5-ön sikerül, a patch elavult → FRISSÍTENI KELL,
#         nem lazítani.
#       - Ha 0.5 sem elég: a patch kontextusa túlságosan eltér,
#         valószínűleg upstream már beolvasztotta → a patchet ki kell venni
#
#  -a / --atomic / --all-or-nothing   (a kettő UGYANAZ)
#     Minden-vagy-semmi. Ha bármely hunk elhasal, egy fájl sem íródik.
#     Build-hez KÖTELEZŐ. Kikapcsolva részleges írás lehetséges, ami
#     csendben elrontja a forrásfát.
#
#     FONTOS: az atomic és a fuzz-factor ORTOGONÁLIS. Az atomic a
#     write-szemantikát szabályozza, a fuzz a match-szemantikát.
#     Az atomic-ot NEM kell a fuzz-hoz igazítani.
#
#     HATÓKÖR: egy mpatch híváson belül garantál atomitást. A while
#     ciklusban minden patch külön hívás → ha a 40. elhasal, az első
#     39 már lemezre íródott. Ez a mi esetünkben OK, mert a prepare()
#     elején úgyis rm -rf "${_pkg}"-vel tiszta lappal indulunk.
#
#  -R                          Patch megfordítása (add ↔ remove).
#                              Build-hez nem kell, de ha egy patch-et
#                              vissza akarsz fejteni (mit is csinál
#                              pontosan), akkor hasznos.
#
#  --dry-run                   Csak előnézet, nem ír fájlt.
#                              Debug workflow 1. lépése: mit tenne?
#
#  -c / --clipboard            Vágólapról olvas. Ilyenkor az INPUT_FILE
#                              elhagyható: `mpatch -c ./src` is működik.
#                              Build-hez nem kell.
#
#  -                           stdin-ről olvas. Pipe esetén a '-' is
#                              elhagyható: `git diff | mpatch ./src`.
#                              Build-hez nem kell (fájlból olvasunk).
#
#  -v / --verbose              Ismételhető, szintenként:
#                                -v     info (mit csinál épp)
#                                -vv    debug
#                                -vvv   trace
#                                -vvvv  trace + debug-riport fájl
#                              Siker esetén az mpatch ALAPBÓL SEMMIT
#                              nem ír ki. Ha a build logban látni akarod
#                              a patchek előrehaladását, tegyél -v-t a
#                              _mpatch_opts-ba.
#
#  -h / --help                 Súgó.
#
#  ---------------------------------------------------------------------------
#  EXIT KÓDOK ÉS KIMENET (a _mpatch_apply logikája erre épül)
#  ---------------------------------------------------------------------------
#
#    Siker (minden hunk alkalmazva)     → exit 0, semmit nem ír ki
#    Hiba (bármely hunk elbukik)        → exit 1, kiírja a legközelebbi
#                                          találatot + hasonlóságot
#    Nincs patch a bemenetben           → warning + exit 0  ⚠ CSAPDA
#
#  ⚠ A "nincs patch → exit 0" csapda: ha egy Debian patch véletlenül
#  üres, vagy csak kommenteket tartalmaz, az mpatch NÉMÁN átengedi,
#  és a build később, érthetetlen módon hasal el. A _mpatch_apply
#  ezt nem tudja kiszűrni – ha gyanús egy patch, nézd meg a tartalmát.
#
#  ⚠ --atomic NÉLKÜL a sikeres hunok lemezre íródnak akkor is, ha
#  más hunok elbuknak → részleges, csendben elrontott forrásfa.
#  Ezért van --atomic kötelezően a _mpatch_opts-ban.
#
#  ---------------------------------------------------------------------------
#  DEBUG WORKFLOW – HA EGY PATCH ELHASAL
#  ---------------------------------------------------------------------------
#
#  1. LÉPÉS – Nézd meg a hibaüzenetet
#     Az mpatch kiírja, melyik fájlt és melyik hunkot nem tudta alkalmazni.
#     A prepare() automatikusan -vvvv-vel újrafuttatja a hibás patchet,
#     és a debug-riportot a ${srcdir}/mpatch-debug/-be másolja.
#
#  2. LÉPÉS – Kizártad a FORMÁTUM-LIMITÁCIÓT?
#     Nézd meg a patch tartalmát:
#       grep -E 'rename from|copy from|GIT binary patch|^diff -c ' <patch>
#     Ha bármelyik találat van: a fuzz nem segít, a patchet ki kell
#     venni vagy kézzel át kell írni. Csak ha üres a találat, menj
#     tovább a 3. lépésre. (Ez a leggyakrabban elfelejtett ellenőrzés.)
#
#  3. LÉPÉS – Nézd meg a debug-riportot
#     mpatch-debug-report-<timestamp>.md a ${srcdir}/mpatch-debug/-ben.
#     Tartalmazza:
#       - az eredeti patch-et
#       - a célfájl érintett részeit
#       - inline word-level diffet a nem illeszkedő hunkról
#       - a legközelebbi hasonló fájlútvonalakat (ha a fájl nem található)
#
#  4. LÉPÉS – Próbáld lazítani a fuzz-factort
#     Szerkeszd a PKGBUILD-ben a _mpatch_opts-ot:
#       --fuzz-factor 0.5
#     Futtasd újra: makepkg -f
#     Ha sikerül: a patch elavult, jegyezd fel, és később frissítsd.
#     Ha nem sikerül: 5. lépés.
#
#  5. LÉPÉS – Reverse-engineer
#     Nézd meg, mit csinál a patch eredetileg:
#       mpatch -R --dry-run <patch> kernel/
#     Ez megmutatja, mit venne ki a forrásból.
#     Nézd meg a Debian upstream git history-t:
#       https://salsa.debian.org/nvidia-team/nvidia-graphics-drivers
#     Keress rá a patch nevére, nézd meg az eredeti commitot.
#
#  6. LÉPÉS – Kihagyás vagy frissítés
#     Ha a patch már upstream-ben van: vedd ki a series.resolved-ból.
#     Ha a patch elavult: frissítsd a Debian salsa repóból.
#     Ha muszáj: írj saját patchet a különbségre.
#
#  ---------------------------------------------------------------------------
#  TESZTELÉSI TIPP
#  ---------------------------------------------------------------------------
#  Egyetlen patch tesztelése a teljes sorozat helyett:
#     cd ${srcdir}/NVIDIA-Linux-x86_64-390.157-no-compat32/kernel
#     mpatch --dry-run --fuzz-factor 0.7 ${srcdir}/<patch> .
#  Ez megmutatja, mit tenne, anélkül hogy bármit írna.
#
# =============================================================================

pkgbase=nvidia-390xx-utils
pkgname=('nvidia-390xx-utils' 'opencl-nvidia-390xx' 'nvidia-390xx-dkms' 'mhwd-nvidia-390xx')
pkgver=390.157
pkgrel=1
arch=('x86_64')
url="https://www.nvidia.com/"
license=('custom')
options=('!strip')
makedepends=('mpatch-git')
_pkg="NVIDIA-Linux-x86_64-${pkgver}-no-compat32"

# =============================================================================
# MPATCH KONFIGURÁCIÓ – ITT ÁLLÍTS, ITT DEBUGOLJ
# =============================================================================
_mpatch_opts=(
    --atomic                # minden-vagy-semmi (build-hez kötelező)
#    --fuzz-factor 0.7       # default hasonlósági küszöb
    # --fuzz-factor 0.9     # szigorúbb: kevesebb eltűrés, több bukás
#    --fuzz-factor 0.3     # lazább: csak debug célra!
    # --fuzz-factor 0.0     # fuzzy kikapcsolva (egzakt + trailing-ws match)
    # --dry-run             # ne írjon, csak mutassa mit tenne
    # -v                    # info szint (siker esetén is ír valamit)
    # -vvvv                 # debug riport hiba esetén (a prepare() auto hívja)
    # -R                    # patch megfordítása (reverse-engineer)
    # -c                    # vágólapról olvas (build-hez nem kell)
    # -                     # stdin-ről olvas (build-hez nem kell)
)

_mpatch_debug_opts=(
    -vvvv
    --dry-run
)

_mpatch_debug_on_failure=1

# ---- Debian patch lista (a series.resolved-ból, sorrend kötelező) ----
_debian_patches=(
    'cc_version_check-gcc5.patch'
    'bashisms.patch'
    'do-div-cast.patch'
    '0001-backport-error-on-unknown-conftests.patch'
    '0002-backport-error-on-unknown-conftests-uvm-part.patch'
    '0003-backport-set_-memory-pages-_array-_uc-changes-from-5.patch'
    '0004-fix-conftest-includes.patch'
    '0008-backport-nvidia-drm-helper.h-inclusion-from-450.51.patch'
    '0021-backport-acpi_op_remove-changes-from-470.182.03.patch'
    '0022-backport-drm_connector_has_override_edid-changes-fro.patch'
    '0023-backport-vm_area_struct_has_const_vm_flags-changes-f.patch'
    '0024-backport-vm_area_struct_has_const_vm_flags-changes-f.patch'
    '0025-backport-drm_driver_has_dumb_destroy-changes-from-52.patch'
    '0026-backport-get_user_pages-changes-from-418.30.patch'
    '0027-backport-get_user_pages-changes-from-520.56.06.patch'
    '0028-backport-get_user_pages-changes-from-525.53.patch'
    '0029-backport-get_user_pages-changes-from-525.53-uvm-part.patch'
    '0030-backport-get_user_pages-changes-from-535.86.05.patch'
    '0031-backport-asm-page.h-changes-from-470.223.02.patch'
    '0032-backport-drm_gem_prime_handle_to_fd-changes-from-470.patch'
    '0033-refuse-to-load-legacy-module-if-IBT-is-enabled.patch'
    '0034-fix-typos.patch'
    '0038-backport-drm_unlocked_ioctl_flag_present-changes-fro.patch'
    '0038-backport-screen_info-changes-from-450.51.patch'
    '0039-backport-screen_info-changes-from-470.182.03.patch'
    '0040-backport-screen_info-changes-from-470.239.06.patch'
    '0041-backport-CONFIG_MITIGATION_RETPOLINE-changes-from-47.patch'
    '0043-backport-follow_pfn-changes-from-550.90.07.patch'
    '0046-backport-nv_get_kern_phys_address-changes-from-555.4.patch'
    '0047-backport-drm_output_poll_changed-changes-from-535.21.patch'
    '0048-backport-cmd_symlink-changes-from-550.142.patch'
    '0049-backport-uvm-warning-fixes-from-396.18.patch'
    '0049-backport-uvm-warning-fixes-from-415.13.patch'
    '0049-backport-uvm-warning-fixes-from-418.30.patch'
    '0049-backport-warning-fixes-from-430.09.patch'
    '0049-backport-uvm-warning-fixes-from-435.17.patch'
    '0049-backport-uvm-warning-fixes-from-510.39.01.patch'
    '0050-backport-uvm-warning-fixes-from-535.146.02.patch'
    '0051-backport-warning-fixes-from-535.216.01.patch'
    '0052-backport-uvm-warning-fixes-from-560.28.03.patch'
    '0053-fix-more-warnings.patch'
    '0054-fix-more-uvm-warnings.patch'
    '0055-backport-file_operations_fop_unsigned_offset_present.patch'
    '0056-backport-LD_SCRIPT-changes-from-535.230.02.patch'
    '0057-backport-uvm-fixes-from-535.230.02.patch'
    '0060-backport-build_cflags-changes-from-525.85.05.patch'
    '0061-backport-drm_gem_object_vmap_has_map_arg-changes-fro.patch'
    '0063-backport-conftest.sh-comment-changes-from-515.48.07.patch'
    '0063-backport-conftest.sh-comment-changes-from-525.53.patch'
    '0063-backport-conftest.sh-comment-changes-from-545.23.06.patch'
    '0064-backport-drm_driver_has_date-from-570.124.04.patch'
    '0065-backport-ccflags-y-changes-from-570.153.02.patch'
    '0066-backport-nv_timer_delete_sync-changes-from-570.153.0.patch'
    '0067-backport-drm_connector_helper_funcs_mode_valid_has_c.patch'
    '0071-backport-nv_vma_start_write-changes-from-570.169.patch'
    '0074-backport-drm_fb_create_takes_format_info-changes-fro.patch'
    '0075-backport-drm_print.h-changes-from-570.211.01.patch'
    '0076-backport-nv_in_hardirq-changes-from-580.119.02.patch'
    '0077-backport-vma_flags_set_word-changes-from-580.126.09.patch'
    '0078-backport-vma_flags_set_word-changes-from-580.126.09-.patch'
    '0079-backport-dma_map_ops_has_map_phys-changes-from-580.1.patch'
    '0080-backport-for_each_-_connector_in_state-changes-from-.patch'
    '0081-backport-for_each_-_crtc_in_state-changes-from-535.3.patch'
    '0082-backport-for_each_-_plane_in_state-changes-from-535..patch'
    '0083-backport-dma_fence_signal-changes-from-535.309.01.patch'
    '0084-backport-is_vma_write_locked_has_mm_lock_seq_arg-cha.patch'
    '0085-backport-drm_atomic_commit_struct_present-changes-fr.patch'
    '0086-backport-strncpy-changes-from-580.178.04.patch'
    '0087-backport-strncpy-changes-from-580.178.04-uvm-part.patch'
    'conftest-verbose.patch'
    'use-kbuild-compiler.patch'
    'use-kbuild-flags.patch'
    'nvidia-use-ARCH.o_binary.patch'
    'nvidia-modeset-use-ARCH.o_binary.patch'
    'include-swiotlb-header-on-arm.patch'
    'ignore_xen_on_arm.patch'
    'arm-outer-sync.patch'
    'nvidia-drm-arm-cflags.patch'
    'armhf-on-arm64-kernel.patch'
    'make-modesetting-default.patch'
    'fixup-warnings.patch'
    'kernel-6.18-workqueue-flush.patch'
    'kernel-6.18-prime-fence-flush.patch'
    'kernel-7.3-acpi.patch'
    'kernel-linux-next-drm-reset.patch'
)

source=("https://us.download.nvidia.com/XFree86/Linux-x86_64/${pkgver}/${_pkg}.run"
        'mhwd-nvidia'
        'nvidia-390xx-utils.install'
        'nvidia-390xx-utils.sysusers'
        'nvidia-390xx.rules'
        'nvidia-390xx-utils.conf'
        'nvidia-390xx-utils-modules-load.conf'
        'nvidia-drm-outputclass.conf'
        'systemd-homed-override.conf'
        'systemd-suspend-override.conf'
        '10_nvidia.json'
        'series.resolved'
        "${_debian_patches[@]}"
)

# Hash-ek: mind SKIP (12 fix fájl + 85 Debian patch = 97 db), hogy a gyakran
# frissülő Debian patchek és helper fájlok ne okozzanak felesleges build-hibát.
sha256sums=('SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP'
            'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP'
            'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP'
            'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP'
            'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP'
            'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP'
            'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP'
            'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP'
            'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP'
            'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP'
            'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP'
            'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP' 'SKIP'
            'SKIP')

# =============================================================================
# SYMLINK GENERÁTOR – a .so SONAME-ekhez szükséges linkek létrehozása.
# Ezt a prepare() után minden package_* függvény meghívja.
# =============================================================================
create_links() {
    find "$pkgdir" -type f -name '*.so*' ! -path '*xorg/*' -print0 | while read -d $'\0' _lib; do
        _soname=$(dirname "${_lib}")/$(readelf -d "${_lib}" | grep -Po 'SONAME.*: \[\K[^]]*' || true)
        _base=$(echo ${_soname} | sed -r 's/(.*)\.so.*/\1.so/')
        [[ -e "${_soname}" ]] || ln -s $(basename "${_lib}") "${_soname}"
        [[ -e "${_base}" ]] || ln -s $(basename "${_soname}") "${_base}"
    done
}

# =============================================================================
# SEGÉDFÜGGVÉNYEK – mpatch wrapperek
# =============================================================================

_mpatch_cmd() {
    printf '%s ' mpatch "${_mpatch_opts[@]}"
}

_mpatch_apply() {
    local _patchfile="$1"
    local _targetdir="$2"
    local _patchname
    _patchname=$(basename "$_patchfile")

    mpatch "${_mpatch_opts[@]}" "$_patchfile" "$_targetdir"
    local _rc=$?

    if [ "$_rc" -eq 0 ]; then
        return 0
    fi

    echo "!!! mpatch FAILED (rc=$_rc): $_patchname" >&2

    if [ "${_mpatch_debug_on_failure}" = "1" ]; then
        local _dbgdir="${srcdir}/mpatch-debug"
        mkdir -p "$_dbgdir"
        echo ">>> Debug riport generálása: $_dbgdir/" >&2
        ( cd "$_targetdir" && mpatch "${_mpatch_debug_opts[@]}" \
            "$_patchfile" . ) > "$_dbgdir/${_patchname}.stdout" 2>&1 || true
        find "${_targetdir}" -maxdepth 1 -name 'mpatch-debug-report-*.md' \
            -exec mv {} "$_dbgdir/${_patchname}.report.md" \; 2>/dev/null || true
        echo ">>> Nézd meg: $_dbgdir/${_patchname}.report.md" >&2
        echo ">>> Ha elakadtál: olvasd el a PKGBUILD fejlécében a" >&2
        echo ">>> 'DEBUG WORKFLOW – HA EGY PATCH ELHASAL' részt." >&2
    fi

    return "$_rc"
}

# =============================================================================
# PREPARE
# =============================================================================
prepare() {
    rm -rf "${_pkg}"
    sh "${_pkg}.run" --extract-only

    cd "${_pkg}"

    bsdtar -xf nvidia-persistenced-init.tar.bz2
    sed -i 's/__NV_VK_ICD__/libGLX_nvidia.so.0/' nvidia_icd.json.template

    cd kernel

    # -------------------------------------------------------------------------
    # Debian patch-sorozat alkalmazása mpatch-csel (series.resolved sorrend)
    # -------------------------------------------------------------------------
    echo ">>> Debian patch-sorozat alkalmazása mpatch-csel (kernel/ könyvtárban)..."
    echo ">>> Opciók: ${_mpatch_opts[*]}"

    if [ ! -f "${srcdir}/series.resolved" ]; then
        echo "!!! HIBA: hiányzik a series.resolved a PKGBUILD mellől"
        echo "!!! A series.resolved a Debian series.in-ből generált,"
        echo "!!! feloldott sorrend (#HAS_UVM# prefixek eltávolítva)."
        exit 1
    fi

    local _n=0
    local _total
    _total=$(grep -cve '^[[:space:]]*$' "${srcdir}/series.resolved")

    while IFS= read -r _patch || [ -n "$_patch" ]; do
        _patch="${_patch%$'\r'}"
        [ -z "${_patch//[[:space:]]/}" ] && continue
        _n=$((_n + 1))
        _patchfile="${srcdir}/${_patch}"

        if [ ! -f "$_patchfile" ]; then
            echo "!!! HIBA: hiányzó patch: $_patchfile"
            echo "!!! Ellenőrizd, hogy a series.resolved-ban szereplő"
            echo "!!! összes patch megvan-e a PKGBUILD mellett."
            exit 1
        fi

        printf '[%3d/%d] %s\n' "$_n" "$_total" "$_patch"
        _mpatch_apply "$_patchfile" . \
            || { echo "!!! PATCH FAILED: $_patch"; exit 1; }
    done < "${srcdir}/series.resolved"

    echo ">>> Mind a $_n patch sikeresen alkalmazva (mpatch)."

    # -------------------------------------------------------------------------
    # 2. Debian build-stamp blob-előkészítés — 390-nél KÉT blob van.
    #    Az eredeti .o_binary-ket átnevezzük arch-specifikusra, hogy a
    #    use-ARCH.o_binary patchek receptjei garantáltan lefussanak és
    #    létrejöjjenek a .cmd fájlok (modpost ne hasaljon el).
    # -------------------------------------------------------------------------
    if [ ! -f nvidia/nv-kernel.o_binary ]; then
        echo "!!! HIBA: hiányzik kernel/nvidia/nv-kernel.o_binary"
        exit 1
    fi
    mv -f nvidia/nv-kernel.o_binary nvidia/nv-kernel-amd64.o_binary
    echo ">>> nvidia/nv-kernel.o_binary → nvidia/nv-kernel-amd64.o_binary"

    if [ ! -f nvidia-modeset/nv-modeset-kernel.o_binary ]; then
        echo "!!! HIBA: hiányzik kernel/nvidia-modeset/nv-modeset-kernel.o_binary"
        exit 1
    fi
    mv -f nvidia-modeset/nv-modeset-kernel.o_binary nvidia-modeset/nv-modeset-kernel-amd64.o_binary
    echo ">>> nvidia-modeset/nv-modeset-kernel.o_binary → nvidia-modeset/nv-modeset-kernel-amd64.o_binary"

    # -------------------------------------------------------------------------
    # 3. DKMS workaround: KERNELRELEASE semlegesítése a top-level make híváskor.
    # -------------------------------------------------------------------------
    {
        cat <<'EOF_HEADER'
# --- DKMS workaround: KERNELRELEASE semlegesítése a top-level híváskor ---
ifeq ($(M),)
  override KERNELRELEASE :=
endif
# --- end DKMS workaround ---
EOF_HEADER
        cat Makefile
    } > Makefile.new
    mv Makefile.new Makefile

    echo ">>> DKMS workaround hozzáadva a kernel/Makefile tetejére."

    # -------------------------------------------------------------------------
    # 4. DKMS dkms.conf előkészítése — 390-nél 4 modul.
    # -------------------------------------------------------------------------
    sed -i "s/__VERSION_STRING/${pkgver}/" dkms.conf
    sed -i 's/__JOBS/`nproc`/' dkms.conf
    sed -i 's/__DKMS_MODULES//' dkms.conf
    sed -i '$iBUILT_MODULE_NAME[0]="nvidia"\
DEST_MODULE_LOCATION[0]="/kernel/drivers/video"\
BUILT_MODULE_NAME[1]="nvidia-uvm"\
DEST_MODULE_LOCATION[1]="/kernel/drivers/video"\
BUILT_MODULE_NAME[2]="nvidia-modeset"\
DEST_MODULE_LOCATION[2]="/kernel/drivers/video"\
BUILT_MODULE_NAME[3]="nvidia-drm"\
DEST_MODULE_LOCATION[3]="/kernel/drivers/video"' dkms.conf

    sed -i 's/NV_EXCLUDE_BUILD_MODULES/IGNORE_PREEMPT_RT_PRESENCE=1 NV_EXCLUDE_BUILD_MODULES/' dkms.conf

    cd ..
}

package_opencl-nvidia-390xx() {
    pkgdesc="OpenCL implemention for NVIDIA"
    depends=('zlib')
    optdepends=('opencl-headers: headers necessary for OpenCL development')
    provides=("opencl-nvidia=${pkgver}" 'opencl-driver')
    conflicts=('opencl-nvidia')

    cd "${_pkg}"

    install -Dm644 nvidia.icd "${pkgdir}/etc/OpenCL/vendors/nvidia.icd"
    install -Dm755 "libnvidia-compiler.so.${pkgver}" "${pkgdir}/usr/lib/libnvidia-compiler.so.${pkgver}"
    install -Dm755 "libnvidia-opencl.so.${pkgver}" "${pkgdir}/usr/lib/libnvidia-opencl.so.${pkgver}"

    create_links

    mkdir -p "${pkgdir}/usr/share/licenses"
    ln -s nvidia "${pkgdir}/usr/share/licenses/opencl-nvidia"
}

package_nvidia-390xx-dkms() {
    pkgdesc="NVIDIA driver sources for linux, 390xx legacy branch"
    depends=('dkms' "nvidia-390xx-utils=${pkgver}" 'libglvnd')
    provides=('NVIDIA-MODULE' "nvidia-dkms=${pkgver}")
    conflicts=('nvidia-dkms')

    cd "${_pkg}"

    install -dm 755 "${pkgdir}"/usr/src
    cp -dr --no-preserve='ownership' kernel "${pkgdir}/usr/src/nvidia-${pkgver}"

    install -Dt "${pkgdir}/usr/share/licenses/${pkgname}" -m644 "${srcdir}/${_pkg}/LICENSE"
}

package_nvidia-390xx-utils() {
    pkgdesc="NVIDIA drivers utilities"
    depends=('xorg-server' 'libglvnd' 'egl-wayland')
    optdepends=("nvidia-390xx-settings=${pkgver}: configuration tool"
                'xorg-server-devel: nvidia-xconfig'
                'opencl-nvidia-390xx: OpenCL support')
    conflicts=('nvidia-libgl' 'nvidia-utils' 'nvidia-390xx-libgl')
    provides=('vulkan-driver' 'opengl-driver' 'nvidia-libgl' "nvidia-utils=${pkgver}" 'nvidia-390xx-libgl')
    replaces=('nvidia-390xx-libgl')
    install="${pkgname}.install"

    cd "${_pkg}"

    # X driver
    install -Dm755 nvidia_drv.so "${pkgdir}/usr/lib/xorg/modules/drivers/nvidia_drv.so"

    # GLX extension module for X
    install -Dm755 "libglx.so.${pkgver}" "${pkgdir}/usr/lib/nvidia/xorg/libglx.so.${pkgver}"
    ln -s "libglx.so.${pkgver}" "${pkgdir}/usr/lib/nvidia/xorg/libglx.so.1"
    ln -s "libglx.so.${pkgver}" "${pkgdir}/usr/lib/nvidia/xorg/libglx.so"

    install -Dm755 "libGLX_nvidia.so.${pkgver}" "${pkgdir}/usr/lib/libGLX_nvidia.so.${pkgver}"

    # OpenGL libraries (GLVND)
    install -Dm755 "libEGL_nvidia.so.${pkgver}"          "${pkgdir}/usr/lib/libEGL_nvidia.so.${pkgver}"
    install -Dm755 "libGLESv1_CM_nvidia.so.${pkgver}"    "${pkgdir}/usr/lib/libGLESv1_CM_nvidia.so.${pkgver}"
    install -Dm755 "libGLESv2_nvidia.so.${pkgver}"       "${pkgdir}/usr/lib/libGLESv2_nvidia.so.${pkgver}"
    install -Dm644 "${srcdir}/10_nvidia.json"            "${pkgdir}/usr/share/glvnd/egl_vendor.d/10_nvidia.json"

    # OpenGL core library
    install -Dm755 "libnvidia-glcore.so.${pkgver}"  "${pkgdir}/usr/lib/libnvidia-glcore.so.${pkgver}"
    install -Dm755 "libnvidia-eglcore.so.${pkgver}" "${pkgdir}/usr/lib/libnvidia-eglcore.so.${pkgver}"
    install -Dm755 "libnvidia-glsi.so.${pkgver}"    "${pkgdir}/usr/lib/libnvidia-glsi.so.${pkgver}"

    # misc
    install -Dm755 "libnvidia-ifr.so.${pkgver}"    "${pkgdir}/usr/lib/libnvidia-ifr.so.${pkgver}"
    install -Dm755 "libnvidia-fbc.so.${pkgver}"    "${pkgdir}/usr/lib/libnvidia-fbc.so.${pkgver}"
    install -Dm755 "libnvidia-encode.so.${pkgver}" "${pkgdir}/usr/lib/libnvidia-encode.so.${pkgver}"
    install -Dm755 "libnvidia-cfg.so.${pkgver}"    "${pkgdir}/usr/lib/libnvidia-cfg.so.${pkgver}"
    install -Dm755 "libnvidia-ml.so.${pkgver}"     "${pkgdir}/usr/lib/libnvidia-ml.so.${pkgver}"

    # Vulkan ICD
    install -Dm644 "nvidia_icd.json.template" "${pkgdir}/usr/share/vulkan/icd.d/nvidia_icd.json"

    # VDPAU
    install -Dm755 "libvdpau_nvidia.so.${pkgver}" "${pkgdir}/usr/lib/vdpau/libvdpau_nvidia.so.${pkgver}"

    # nvidia-tls library
    install -Dm755 "tls/libnvidia-tls.so.${pkgver}" "${pkgdir}/usr/lib/libnvidia-tls.so.${pkgver}"

    # CUDA
    install -Dm755 "libcuda.so.${pkgver}"    "${pkgdir}/usr/lib/libcuda.so.${pkgver}"
    install -Dm755 "libnvcuvid.so.${pkgver}" "${pkgdir}/usr/lib/libnvcuvid.so.${pkgver}"

    # PTX JIT Compiler
    install -Dm755 "libnvidia-ptxjitcompiler.so.${pkgver}" "${pkgdir}/usr/lib/libnvidia-ptxjitcompiler.so.${pkgver}"

    # Fat binary loader
    install -Dm755 "libnvidia-fatbinaryloader.so.${pkgver}" "${pkgdir}/usr/lib/libnvidia-fatbinaryloader.so.${pkgver}"

    # DEBUG
    install -Dm755 nvidia-debugdump "${pkgdir}/usr/bin/nvidia-debugdump"

    # nvidia-xconfig
    install -Dm755 nvidia-xconfig "${pkgdir}/usr/bin/nvidia-xconfig"
    install -Dm644 nvidia-xconfig.1.gz "${pkgdir}/usr/share/man/man1/nvidia-xconfig.1.gz"

    # nvidia-bug-report
    install -Dm755 nvidia-bug-report.sh "${pkgdir}/usr/bin/nvidia-bug-report.sh"

    # nvidia-smi
    install -Dm755 nvidia-smi "${pkgdir}/usr/bin/nvidia-smi"
    install -Dm644 nvidia-smi.1.gz "${pkgdir}/usr/share/man/man1/nvidia-smi.1.gz"

    # nvidia-cuda-mps
    install -Dm755 nvidia-cuda-mps-server "${pkgdir}/usr/bin/nvidia-cuda-mps-server"
    install -Dm755 nvidia-cuda-mps-control "${pkgdir}/usr/bin/nvidia-cuda-mps-control"
    install -Dm644 nvidia-cuda-mps-control.1.gz "${pkgdir}/usr/share/man/man1/nvidia-cuda-mps-control.1.gz"

    # nvidia-modprobe
    install -Dm4755 nvidia-modprobe "${pkgdir}/usr/bin/nvidia-modprobe"
    install -Dm644 nvidia-modprobe.1.gz "${pkgdir}/usr/share/man/man1/nvidia-modprobe.1.gz"

    # nvidia-persistenced
    install -Dm755 nvidia-persistenced "${pkgdir}/usr/bin/nvidia-persistenced"
    install -Dm644 nvidia-persistenced.1.gz "${pkgdir}/usr/share/man/man1/nvidia-persistenced.1.gz"
    install -Dm644 nvidia-persistenced-init/systemd/nvidia-persistenced.service.template \
        "${pkgdir}/usr/lib/systemd/system/nvidia-persistenced.service"
    sed -i 's/__USER__/nvidia-persistenced/' "${pkgdir}/usr/lib/systemd/system/nvidia-persistenced.service"

    # application profiles
    install -Dm644 nvidia-application-profiles-${pkgver}-rc \
        "${pkgdir}/usr/share/nvidia/nvidia-application-profiles-${pkgver}-rc"
    install -Dm644 nvidia-application-profiles-${pkgver}-key-documentation \
        "${pkgdir}/usr/share/nvidia/nvidia-application-profiles-${pkgver}-key-documentation"

    install -Dm644 LICENSE "${pkgdir}/usr/share/licenses/nvidia/LICENSE"
    ln -s nvidia "${pkgdir}/usr/share/licenses/nvidia-utils"
    install -Dm644 README.txt "${pkgdir}/usr/share/doc/nvidia/README"
    install -Dm644 NVIDIA_Changelog "${pkgdir}/usr/share/doc/nvidia/NVIDIA_Changelog"
    cp -r html "${pkgdir}/usr/share/doc/nvidia/"
    ln -s nvidia "${pkgdir}/usr/share/doc/nvidia-utils"

    # systemd overrides (Systemd 256)
    install -Dm644 "${srcdir}/systemd-homed-override.conf" \
        "${pkgdir}/usr/lib/systemd/system/systemd-homed.service.d/10-nvidia-no-freeze-session.conf"
    install -Dm644 "${srcdir}/systemd-suspend-override.conf" \
        "${pkgdir}/usr/lib/systemd/system/systemd-suspend.service.d/10-nvidia-no-freeze-session.conf"
    install -Dm644 "${srcdir}/systemd-suspend-override.conf" \
        "${pkgdir}/usr/lib/systemd/system/systemd-suspend-then-hibernate.service.d/10-nvidia-no-freeze-session.conf"
    install -Dm644 "${srcdir}/systemd-suspend-override.conf" \
        "${pkgdir}/usr/lib/systemd/system/systemd-hibernate.service.d/10-nvidia-no-freeze-session.conf"
    install -Dm644 "${srcdir}/systemd-suspend-override.conf" \
        "${pkgdir}/usr/lib/systemd/system/systemd-hybrid-sleep.service.d/10-nvidia-no-freeze-session.conf"

    # Xorg outputclass (Manjaro-specifikus)
    install -Dm644 "${srcdir}/nvidia-drm-outputclass.conf" \
        "${pkgdir}/usr/share/X11/xorg.conf.d/10-nvidia-drm-outputclass.conf"

    # udev rules
    install -Dm644 "${srcdir}/nvidia-390xx.rules" \
        "${pkgdir}/usr/lib/udev/rules.d/60-nvidia-390xx.rules"

    # sysusers
    install -Dm644 "${srcdir}/nvidia-390xx-utils.sysusers" \
        "${pkgdir}/usr/lib/sysusers.d/${pkgname}.conf"

    # -----------------------------------------------------------------------
    # modprobe.d: blacklist + softdep (fájlból, echo nélkül)
    # -----------------------------------------------------------------------
    install -Dm644 "${srcdir}/nvidia-390xx-utils.conf" \
        "${pkgdir}/usr/lib/modprobe.d/nvidia-390xx-utils.conf"

    # -----------------------------------------------------------------------
    # modules-load.d: nvidia-uvm (fájlból, echo nélkül)
    # -----------------------------------------------------------------------
    install -Dm644 "${srcdir}/nvidia-390xx-utils-modules-load.conf" \
        "${pkgdir}/usr/lib/modules-load.d/${pkgname}.conf"

    create_links
}

package_mhwd-nvidia-390xx() {
    pkgdesc="MHWD module-ids for nvidia ${pkgver}"
    arch=('any')
    depends=('mhwd')

    install -d -m755 "${pkgdir}/var/lib/mhwd/ids/pci/"

    sh -e ${srcdir}/mhwd-nvidia \
        ${srcdir}/${_pkg}/README.txt \
        ${srcdir}/${_pkg}/kernel/nvidia/nv-kernel-amd64.o_binary \
        > ${pkgdir}/var/lib/mhwd/ids/pci/nvidia-390xx.ids

    sed -i 's/1b81 1b84/1b81 1b82 1b84/g' ${pkgdir}/var/lib/mhwd/ids/pci/nvidia-390xx.ids
}