#!/usr/bin/env python3
import argparse
import subprocess
import os
import shutil
import urllib.request
import tarfile
import zipfile
import glob
import sys

class Settings:
    jdk_url="http://download.oracle.com/otn-pub/java/jdk/8u131-b11/d54c1d3a095b4ff2b6607d096fa80163/jdk-8u131-linux-x64.tar.gz"
    sdk_tgz_url = "https://dl.google.com/android/repository/sdk-tools-linux-4333796.zip"
    ndk_zip_url = "https://dl.google.com/android/repository/android-ndk-r20-linux-x86_64.zip"

    min_api = {
        "armeabi-v7a" : "16",
        "x86" : "17",
        "x86_64" : "21",
        "arm64-v8a" : "21"
        }
    # see https://developer.android.com/ndk/guides/abis.html
    architectures = ["armeabi-v7a", "x86", "x86_64", "arm64-v8a"]
    freetype_url = "http://download.savannah.gnu.org/releases/freetype/freetype-2.7.tar.bz2"
    ogg_url = "http://downloads.xiph.org/releases/ogg/libogg-1.3.2.tar.xz"
    vorbis_url = "http://downloads.xiph.org/releases/vorbis/libvorbis-1.3.5.tar.xz"
    #png_url = "https://download.sourceforge.net/libpng/libpng-1.6.37.tar.xz"
    physfs_url = "https://icculus.org/physfs/downloads/physfs-3.0.2.tar.bz2"
    flac_url = "https://ftp.osuosl.org/pub/xiph/releases/flac/flac-1.3.2.tar.xz"
    opus_url = "https://archive.mozilla.org/pub/opus/opus-1.3.1.tar.gz"
    opusfile_url = "https://archive.mozilla.org/pub/opus/opusfile-0.9.tar.gz"
    dumb_url = "https://github.com/kode54/dumb/archive/master.zip", "dumb.zip"
    minimp3_url = "https://github.com/lieff/minimp3/archive/master.zip", "minimp3.zip"
    #theora_url = "https://git.xiph.org/?p=theora.git;a=snapshot;h=HEAD;sf=tgz", "theora.tar.gz"
    build_tools_version = "28.0.0"
    
s = Settings()

def main():
    global args
    path = os.getcwd()
    p = argparse.ArgumentParser()
    p.add_argument("-i", "--install", action = "store_true")
    p.add_argument("-b", "--build", action = "store_true")
    p.add_argument("-p", "--package", action = "store_true")
    p.add_argument("-d", "--dist", action = "store_true")
    p.add_argument("-a", "--allegro", help = "path to allegro")
    p.add_argument("-P", "--path", help = "path to install to, by default current directory")
    p.add_argument("-A", "--arch", help = "comma separated list of architectures, by default all are built: " + (", ".join(Settings.architectures)))
    p.add_argument("-D", "--debug", action = "store_true", help = "build debug libraries")
    p.add_argument("-E", "--extra", help = "extra version suffix")

    args = p.parse_args()
    if not args.path:
        args.path = os.getcwd()
    s.log = open(args.path + "/install_android.log", "w")

    if args.arch:
        archs = args.arch.split(",")
        for a in archs:
            if a not in s.architectures:
                sys.stderr.write("Unknown architecture " + a + "\n")
                sys.exit(-1)
        s.architectures = archs
    s.sdk = download_and_unpack(s.sdk_tgz_url, "tools")
    s.ndk = download_and_unpack(s.ndk_zip_url)
    setup_jdk()
    
    if args.install:
        install_sdk()
        install_ndk()
        install_freetype()
        install_ogg()
        install_vorbis()
        # not supported on Android right now, always uses native png()
        install_physfs()
        install_flac()
        install_opus()
        install_opusfile()
        install_dumb()
        install_minimp3()
        # can't get it to compile for android install_theora()

    if args.build or args.package:
        if not args.allegro:
            print("Need -a option to build/package!")
            return

        os.chdir(path)
        args.allegro = os.path.abspath(args.allegro)
        print("Allegro found at", args.allegro)

        parse_version()
        if not s.version:
            print("Cannot find version!")
            return
        
    if args.build:
        build_allegro()

    if args.package:
        print("Packaging version", s.version)
        build_aar()

def parse_version():
    x = [
        "#define ALLEGRO_VERSION ",
        "#define ALLEGRO_SUB_VERSION ",
        "#define ALLEGRO_WIP_VERSION ",
        "#define ALLEGRO_RELEASE_NUMBER "]
    v = []
    for row in open(args.allegro + "/include/allegro5/base.h"):
        for i in range(4):
            if row.startswith(x[i]):
                v.append(row[len(x[i]):].strip(" \"\n"))
    s.version = ".".join(v)
    if args.extra:
        s.version += args.extra

def com(*args, input = None):
    args = [x for x in args if x is not None]
    print(" ".join(args))
    s.log.write(" ".join(args) + "\n")
    try:
        r = subprocess.run(args, check = True, input = input,
            env = os.environ,
            stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        r = e
        sys.stderr.write(" ______\n")
        sys.stderr.write("/FAILED\\\n")
        sys.stderr.write("´`´`´`´`\n")
        s.log.write("FAILED\n")
    if r.stdout:
        s.log.write(r.stdout.decode("utf8") + "\n")
    
def makedirs(name):
    s.log.write("mkdir -p " + name + "\n")
    print("mkdir -p " + name)
    os.makedirs(name, exist_ok = True)

def chdir(name):
    s.log.write("cd " + name + "\n")
    print("cd " + name)
    os.chdir(name)

def write(name, contents, placeholders = {}):
    print("create", name)
    contents = contents.replace("{", "{{")
    contents = contents.replace("}", "}}")
    contents = contents.replace("«", "{")
    contents = contents.replace("»", "}")
    contents = contents.format(**placeholders)
    open(name, "w").write(contents.strip() + "\n")

def copy(source, destination):
    com("cp", "-r", source, destination)

def replace(name, what, whatwith):
    print("edit", name)
    x = open(name, "r").read()
    x = x.replace(what, whatwith)
    open(name, "w").write(x)

def rm(pattern):
    for f in glob.glob(pattern):
        os.unlink(f)

def download(url, path):
    if not os.path.exists(path):
        print("Downloading", url)

        req = urllib.request.Request(url)
        req.add_header("Cookie", "oraclelicense=accept-securebackup-cookie")
        r = urllib.request.urlopen(req)
        with open(path + ".part", "wb") as f:
            f.write(r.read())
        os.rename(path + ".part", path)

def download_and_unpack(url, sub_folder = None):
    if type(url) is tuple:
        url, dest = url
    else:
        slash = url.rfind("/")
        dest = url[slash + 1:]
    print("Checking", url)
    os.makedirs(args.path + "/downloads", exist_ok = True)
    name = args.path + "/downloads/" + dest
    download(url, name)

    dot = name.rfind(".")
    folder = name[:dot]
    if folder.endswith(".tar"):
        folder = folder[:-4]
    target_folder = folder
    if sub_folder:
        target_folder += "/" + sub_folder
    if not os.path.exists(target_folder):
        shutil.rmtree(target_folder + ".part", ignore_errors = True)
        os.makedirs(target_folder + ".part", exist_ok = True)

        print("Unpacking", name)
        if zipfile.is_zipfile(name):
            # doesn't preserve permissions in some python versions
            #with zipfile.ZipFile(name) as z:
            #    z.extractall(folder + ".part")
            com("unzip", "-q", "-d", target_folder + ".part", name)
        else:
            tarfile.open(name).extractall(target_folder + ".part")

        for sub in glob.glob(target_folder + ".part/*"):
            if os.path.isdir(sub):
                shutil.move(sub, folder)
                break
        os.rmdir(target_folder + ".part")

    return folder

def setup_jdk():
    s.jdk = download_and_unpack(s.jdk_url)
    set_var("JAVA_HOME", s.jdk + "/jre")

def install_sdk():
    components = [
        "platform-tools",
        "build-tools;" + s.build_tools_version,
        "platforms;android-28"
        ]
    sdkmanager = s.sdk + "/tools/bin/sdkmanager"
    for component in components:
        com(sdkmanager, component, "--sdk_root=" + s.sdk, input = b"y\n")

def install_ndk():
    for arch in s.architectures:
        install = args.path + "output-" + arch.replace(" ", "_")
        if os.path.exists(install):
            continue
        print("Creating installation for", arch)
        com("mkdir", install)

def set_var(key, val):
    print(key + "=" + val)
    os.environ[key] = val

def add_path(val):
    print("PATH=" + val + ":${PATH}")
    os.environ["PATH"] = val + ":" + os.environ["PATH"]

def backup_path():
    s.backup_path = os.environ["PATH"]

def restore_path():
    os.environ["PATH"] = s.backup_path

# see https://developer.android.com/ndk/guides/other_build_systems
def setup_host(arch):
    toolchain = s.ndk + "/toolchains/llvm/prebuilt/linux-x86_64" # this is the host architecture, not what we are building

    host2 = None
    if arch == "x86":
        host = "i686-linux-android"
    if arch == "x86_64":
        host = arch + "-linux-android"
    if arch == "armeabi-v7a":
        host = "arm-linux-androideabi"
        host2 = "armv7a-linux-androideabi"
    if arch == "arm64-v8a":
        host = "aarch64-linux-android"
    if host2 is None:
        host2 = host

    minsdk = s.min_api[arch]
    install = args.path + "/output-" + arch.replace(" ", "_")

    set_var("ANDROID_NDK_ROOT", s.ndk)
    set_var("ANDROID_HOME", s.sdk)
    set_var("ANDROID_NDK_TOOLCHAIN_ROOT", toolchain)
    set_var("PKG_CONFIG_LIBDIR", toolchain + "/lib/pkgconfig")
    set_var("PKG_CONFIG_PATH", install + "/lib/pkgconfig")
    set_var("AR", toolchain + "/bin/" + host + "-ar")
    set_var("AS", toolchain + "/bin/" + host + "-as")
    set_var("LD", toolchain + "/bin/" + host + "-ld")
    set_var("RANLIB", toolchain + "/bin/" + host + "-ranlib")
    set_var("STRIP", toolchain + "/bin/" + host + "-strip")
    set_var("CC", toolchain + "/bin/" + host2 + minsdk + "-clang")
    set_var("CXX", toolchain + "/bin/" + host2 + minsdk + "-clang++")
    set_var("CFLAGS", "-fPIC")
    backup_path()
    add_path(s.ndk)
    add_path(s.sdk)
    add_path(toolchain + "/bin")

    #com(host + "-gcc", "-v")

    return host, install

def build_architectures(path, configure):
    slash = path.rfind("/")
    name = path[slash + 1:]
    for arch in s.architectures:
        print("Building", path, "for", arch)
        host, install = setup_host(arch)
        
        destination = install + "/build/" + name
        if not os.path.exists(destination):
            shutil.copytree(path, destination)
        chdir(destination)
        
        configure(arch, host, install)
        restore_path()

def configure_f(*extras):
    def f(arch, host, prefix):
        if not os.path.exists("configure"):
            com("./autogen.sh")
        com("./configure", "--host=" + host, "--prefix=" + prefix, *extras)
        com("make", "-j4")
        com("make", "install")
    return f

def cmake_f(*extras):
    cmake_toolchain = s.ndk + "/build/cmake/android.toolchain.cmake"
    def f(arch, host, prefix):
        com("cmake", "-DCMAKE_TOOLCHAIN_FILE=" + cmake_toolchain,
            "-DANDROID_ABI=" + arch,
            "-DCMAKE_INSTALL_PREFIX=" + prefix,
            *extras)
        com("make", "-j4")
        com("make", "install")
    return f

def install_freetype():
    ft_orig = download_and_unpack(s.freetype_url)
    build_architectures(ft_orig, configure_f("--without-png", "--without-harfbuzz",
            "--with-zlib=no",
            "--with-bzip2=no"))

def install_ogg():
    ogg_orig = download_and_unpack(s.ogg_url)
    build_architectures(ogg_orig, configure_f())

def install_vorbis():
    vorbis_orig = download_and_unpack(s.vorbis_url)
    
    # need to patch libvorbis 1.3.5 to work with clang on i386
    print("Patching libvorbis 1.3.5")
    b = open(vorbis_orig + "/configure").read()
    b = b.replace("-mno-ieee-fp", "")
    open(vorbis_orig + "/configure", "w").write(b)

    build_architectures(vorbis_orig, configure_f())

def install_png():
    png_orig = download_and_unpack(s.png_url)
    build_architectures(png_orig, configure_f())

def install_physfs():
    physfs_orig = download_and_unpack(s.physfs_url)
    build_architectures(physfs_orig, cmake_f("-DPHYSFS_BUILD_SHARED=OFF"))

def install_flac():
    flac_orig = download_and_unpack(s.flac_url)
    build_architectures(flac_orig, configure_f(
            "--disable-cpplibs", "--disable-shared", "--enable-static", "--disable-ogg"))

def install_opus():
    opus_orig = download_and_unpack(s.opus_url)
    build_architectures(opus_orig, configure_f(
            "--disable-shared", "--enable-static"))

def install_opusfile():
    orig = download_and_unpack(s.opusfile_url)
    build_architectures(orig, configure_f(
            "--disable-shared", "--enable-static"))

def install_dumb():
    dumb_orig = download_and_unpack(s.dumb_url)
    build_architectures(dumb_orig, cmake_f("-DBUILD_EXAMPLES=OFF", "-DBUILD_ALLEGRO4=OFF"))

def install_minimp3():
    orig = download_and_unpack(s.minimp3_url)
    def f(arch, host, install):
        com("cp", "minimp3.h", install + "/include/")
        com("cp", "minimp3_ex.h", install + "/include/")
    build_architectures(orig, f)

def install_theora():
    orig = download_and_unpack(s.theora_url)
    build_architectures(orig, configure_f(
            "--disable-shared", "--enable-static"))

def build_allegro():
    for arch in s.architectures:
        print("Building Allegro for", arch)
        
        host, install = setup_host(arch)
        build = install + "/build/allegro"
        if args.debug:
            build += "-debug"
        shutil.rmtree(build, ignore_errors = True)
        makedirs(build)
        chdir(build)

        cmake_toolchain = s.ndk + "/build/cmake/android.toolchain.cmake"

        extra = None
        if arch == "armeabi":
            extra = "-DWANT_ANDROID_LEGACY=on"

        debug = "Release"
        if args.debug:
            debug = "Debug"
        include = install + "/include"
        com("cmake", args.allegro, "-DCMAKE_TOOLCHAIN_FILE=" + cmake_toolchain,
            "-DANDROID_ABI=" + arch,
            "-DCMAKE_BUILD_TYPE=" + debug,
            "-DANDROID_TARGET=android-26",
            "-DCMAKE_INSTALL_PREFIX=" + install,
            extra,
            "-DWANT_DEMO=off",
            "-DWANT_EXAMPLES=off",
            "-DWANT_TESTS=off",
            "-DWANT_DOCS=off",
            "-DPKG_CONFIG_EXECUTABLE=/usr/bin/pkg-config",
            "-DOGG_LIBRARY=" + install + "/lib/libogg.a",
            "-DOGG_INCLUDE_DIR=" + include,
            "-DVORBIS_LIBRARY=" + install + "/lib/libvorbis.a",
            "-DVORBIS_INCLUDE_DIR=" + include,
            "-DVORBISFILE_LIBRARY=" + install + "/lib/libvorbisfile.a",
            "-DSUPPORT_VORBIS=true",
            "-DFREETYPE_LIBRARY=" + install + "/lib/libfreetype.a",
            "-DFREETYPE_INCLUDE_DIRS=" + install + "/include;" + install + "/include/freetype2",
            #"-DPNG_INCLUDE_DIR=" + install + "/include",
            #"-DPNG_LIBRARY=" + install + "/lib/libpng.a",
            "-DFLAC_LIBRARY=" + install + "/lib/libFLAC.a",
            "-DFLAC_INCLUDE_DIR=" + include,
            "-DPHYSFS_LIBRARY=" + install + "/lib/libphysfs.a",
            "-DPHYSFS_INCLUDE_DIR=" + include,
            "-DOPUS_LIBRARY=" + install + "/lib/libopus.a",
            "-DOPUS_INCLUDE_DIR=" + include + "/opus",
            "-DOPUSFILE_LIBRARY=" + install + "/lib/libopusfile.a",
            "-DDUMB_LIBRARY=" + install + "/lib/libdumb.a",
            "-DDUMB_INCLUDE_DIR=" + include,
            "-DMINIMP3_INCLUDE_DIRS=" + include,
            #"-DTHEORA_LIBRARY=" + install + "/lib/libtheora.a",
            #"-DTHEORA_INCLUDE_DIR=" + include,
            )
            
        com("make", "-j4", "VERBOSE=1")
        # Get rid of previously installed files, so for example we get
        # no debug libaries in a release build.
        rm(install + "/lib/liballegro*")
        com("make", "install")
        
        restore_path()

def build_aar():
    shutil.rmtree(args.path + "/gradle_project", ignore_errors = True)
    copy(args.allegro + "/android/gradle_project", args.path + "/gradle_project")
    
    allegro5 = args.path + "/gradle_project/allegro"
    includes = args.path + "/gradle_project/allegro_jni_includes"

    for arch in s.architectures:
        install = args.path + "/output-" + arch.replace(" ", "_")
        makedirs(allegro5 + "/src/main/jniLibs/" + arch)
        for so in glob.glob(install + "/lib/liballeg*"):
            copy(so, allegro5 + "/src/main/jniLibs/" + arch + "/")
    
    makedirs(includes + "/jniIncludes")
    # Note: the Allegro headers are the same for all architectures, so just copy from the first one
    copy(args.path + "/output-" + s.architectures[0] + "/include/allegro5",   includes + "/jniIncludes/")
    copy(allegro5 + "/src/main/jniLibs", includes)

    write(includes + "/allegro.cmake",
"""
get_filename_component(ABI ${CMAKE_BINARY_DIR} NAME)
set(base ${CMAKE_CURRENT_LIST_DIR})

macro(standard_library NAME)
    string(TOUPPER ${NAME} UNAME)
    find_library(LIB_${UNAME} ${NAME})
    target_link_libraries(${NATIVE_LIB} ${LIB_${UNAME}})
endmacro()

macro(allegro_library NAME)
    string(TOUPPER ${NAME} UNAME)
    set(path ${JNI_FOLDER}/jniLibs/${ABI}/lib${NAME})
    if(EXISTS "${path}-debug.so")
        set(LIB_${UNAME} ${path}-debug.so)
    elseif(EXISTS "${path}.so")
        set(LIB_${UNAME} ${path}.so)
    else()
        message(SEND_ERROR "${path}.so does not exist")
    endif()
    target_link_libraries(${NATIVE_LIB} ${LIB_${UNAME}})
endmacro()

include_directories(${JNI_FOLDER}/jniIncludes)
allegro_library(allegro)
allegro_library(allegro_acodec)
allegro_library(allegro_audio)
allegro_library(allegro_color)
allegro_library(allegro_font)
allegro_library(allegro_image)
allegro_library(allegro_primitives)
allegro_library(allegro_ttf)
standard_library(m)
standard_library(z)
standard_library(log)
standard_library(GLESv2)
""")
    write(allegro5 + "/src/main/AndroidManifest.xml", """
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="org.liballeg.android">
</manifest>
""".lstrip())
    write(args.path + "/gradle_project/gradle.properties", """
org.gradle.java.home={}
""".format(s.jdk))
    write(args.path + "/gradle_project/local.properties", """
ndk.dir={}
sdk.dir={}
""".format(s.ndk, s.sdk))
    write(args.path + "/gradle_project/build.gradle", """
buildscript {
    repositories {
        google()
        jcenter()
    }
    dependencies {
        classpath 'com.android.tools.build:gradle:3.1.0'
    }
}
""")
    debug = "debug" if args.debug else "release"
    write(allegro5 + "/build.gradle", """
plugins {
    id "com.jfrog.bintray" version "1.7"
    id "com.github.dcendents.android-maven" version "1.5"
}
apply plugin: 'com.android.library'

android {
    compileSdkVersion 28
    defaultConfig {
        minSdkVersion 17
        targetSdkVersion 28
        versionCode 1
        versionName "«version»"
    }
}
repositories {
    google()
    jcenter()
}
dependencies {
    implementation 'com.android.support:appcompat-v7:28.0.0'
}
archivesBaseName = "allegro5-«debug»"
group = "org.liballeg"
version = "«version»"
task sourcesJar(type: Jar) {
    from android.sourceSets.main.java.srcDirs
    classifier = 'sources'
}
task javadoc(type: Javadoc) {
    source = android.sourceSets.main.java.srcDirs
    classpath += project.files(android.getBootClasspath().join(File.pathSeparator))
}
task javadocJar(type: Jar, dependsOn: javadoc) {
    classifier = 'javadoc'
    from javadoc.destinationDir
}

artifacts {
    archives javadocJar
    archives sourcesJar
}

install {
    repositories.mavenInstaller {
        pom.project {
            name 'allegro5-«debug»'
            description 'Allegro for Android'
            url 'http://liballeg.org'
            inceptionYear '1995'
            artifactId "allegro5-«debug»"

            packaging 'aar'
            groupId 'org.liballeg'
            version '«version»'

            licenses {
                license {
                    name 'zlib'
                    url 'http://liballeg.org/license.html'
                    distribution 'repo'
                }
            }
            scm {
                connection 'https://github.com/liballeg/allegro5.git'
                url 'https://github.com/liballeg/allegro5'

            }
            developers {
                developer {
                    name 'Allegro Developers'
                }
            }
        }
    }
}

Properties properties = new Properties()
File f = "../bintray.properties" as File
properties.load(f.newDataInputStream())
// needs a file bintray.properties with this inside:
// bintray.user = <bintray user>
// bintray.key = <bintray api key>

bintray {   
    user = properties.getProperty("bintray.user")
    key = properties.getProperty("bintray.key")
    configurations = ['archives']
    pkg {
        repo = 'maven'
        name = 'allegro5-«debug»'
        userOrg = 'liballeg'
        licenses = ['zlib']
        vcsUrl = 'https://github.com/liballeg/allegro5.git'
        version {
            name = '«version»'
        }
        publish = true
    }
}
""", {"version" : s.version, "debug" : debug, "build_tools_version" : s.build_tools_version})
    write(args.path + "/gradle_project/settings.gradle", "include ':allegro'")
   
    chdir(args.path + "/gradle_project")
    d = "-debug" if args.debug else ""
    com("zip", "-r", "allegro_jni_includes" + d + ".zip", "allegro_jni_includes")

    if args.dist:
        com("./gradlew", "bintrayUpload")
        makedirs("/var/www/allegro5.org/android/" + s.version)
        copy("allegro_jni_includes" + d + ".zip", "/var/www/allegro5.org/android/" + s.version)

if __name__ == "__main__":
    main()
