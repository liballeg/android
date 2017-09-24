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
    jdk_url = "http://download.oracle.com/otn-pub/java/jdk/8u144-b01/090f390dda5b47b9b721c7dfaa008135/jdk-8u144-linux-x64.tar.gz"
    sdk_tgz_url = "https://dl.google.com/android/repository/sdk-tools-linux-3859397.zip"
    ndk_zip_url = "https://dl.google.com/android/repository/android-ndk-r16-beta1-linux-x86_64.zip"

    min_api = {
        "armeabi" : "15",
        "armeabi-v7a" : "15",
        "x86" : "15",
        "x86_64" : "21",
        "arm64-v8a" : "21",
        "mips" : "15",
        "mips64" : "21"}
    architectures = ["armeabi", "armeabi-v7a", "x86", "x86_64", "arm64-v8a", "mips", "mips64"]
    freetype_url = "http://download.savannah.gnu.org/releases/freetype/freetype-2.7.tar.bz2"
    ogg_url = "http://downloads.xiph.org/releases/ogg/libogg-1.3.2.tar.xz"
    vorbis_url = "http://downloads.xiph.org/releases/vorbis/libvorbis-1.3.5.tar.xz"
    build_tools_version = "26.0.1"
    
s = Settings()

def main():
    global args
    path = os.getcwd()
    p = argparse.ArgumentParser()
    p.add_argument("-i", "--no-install", action = "store_true")
    p.add_argument("-b", "--no-build", action = "store_true")
    p.add_argument("-d", "--no-dist", action = "store_true")
    p.add_argument("-a", "--allegro", help = "path to allegro")
    p.add_argument("-p", "--path", help = "path to install to, by default current directory")
    p.add_argument("-A", "--arch", help = "comma separated list of architectures, by default all are built")
    p.add_argument("-D", "--debug", action = "store_true", help = "build debug libraries")
    p.add_argument("-E", "--extra", help = "extra version suffix")

    args = p.parse_args()
    if not args.path:
        args.path = os.getcwd()
    s.log = open(args.path + "/install_android.log", "w")

    if args.arch:
        s.architectures = args.arch.split(",")
    s.sdk = download_and_unpack(s.sdk_tgz_url, "tools")
    s.ndk = download_and_unpack(s.ndk_zip_url)
    setup_jdk()
    
    if not args.no_install:
        install_sdk()
        install_ndk()
        install_freetype()
        install_ogg()
        install_vorbis()

    if not args.no_build or not args.no_dist:
        if not args.allegro:
            print("Need -a option to build/distribute!")
            return

        os.chdir(path)
        args.allegro = os.path.abspath(args.allegro)
        print("Allegro found at", args.allegro)

        parse_version()
        if not s.version:
            print("Cannot find version!")
            return
        
    if not args.no_build:
        build_allegro()

    if not args.no_dist:
        print("Distributing version", s.version)
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
    print("Checking", url)
    slash = url.rfind("/")
    name = args.path + "/" + url[slash + 1:]
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
    set_var("JAVA_HOME", s.jdk)

def install_sdk():
    components = [
        "platform-tools",
        "build-tools;" + s.build_tools_version,
        "platforms;android-26",
        "extras;android;m2repository"
        ]
    sdkmanager = s.sdk + "/tools/bin/sdkmanager"
    for component in components:
        com(sdkmanager, component, "--sdk_root=" + s.sdk, input = b"y\n")

def install_ndk():
    for arch in s.architectures:
        toolchain = args.path + "/toolchain-" + arch
        if os.path.exists(toolchain):
            continue
        print("Creating toolchain for", arch)
        arch2 = arch
        if arch2 in ["armeabi", "armeabi-v7a"]:
            arch2 = "arm"
        if arch2 == "arm64-v8a":
            arch2 = "arm64"
        com("python", s.ndk + "/build/tools/make_standalone_toolchain.py",
            "--arch", arch2, "--api", s.min_api[arch],
            "--install-dir", toolchain)

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

def setup_host(arch):
    toolchain = args.path + "/toolchain-" + arch
    host = arch + "-linux-android"

    if arch == "x86":
        host = "i686-linux-android"
    if arch == "x86_64":
        host = arch + "-linux-android"
    if arch == "armeabi":
        host = "arm-linux-androideabi"
    if arch == "armeabi-v7a":
        host = "arm-linux-androideabi"
    if arch == "arm64-v8a":
        host = "aarch64-linux-android"
    if arch == "mips":
        host = arch + "el-linux-android"
    if arch == "mips64":
        host = arch + "el-linux-android"

    set_var("ANDROID_NDK_ROOT", s.ndk)
    set_var("ANDROID_HOME", s.sdk)
    set_var("ANDROID_NDK_TOOLCHAIN_ROOT", toolchain)
    set_var("PKG_CONFIG_LIBDIR", toolchain + "/lib/pkgconfig")
    if host == "arm-linux-androideabi":
        # clang for arm crashes :(
        set_var("CC", host + "-gcc")
        set_var("CXX", host + "-g++")
    else:
        set_var("CC", host + "-clang")
        set_var("CXX", host + "-clang++")
    backup_path()
    add_path(s.ndk)
    add_path(s.sdk)
    add_path(toolchain + "/bin")

    #com(host + "-gcc", "-v")

    return host, toolchain

def build_architectures(path, configure):
    slash = path.rfind("/")
    name = path[slash + 1:]
    for arch in s.architectures:
        print("Building", path, "for", arch)
        host, toolchain = setup_host(arch)
        
        destination = toolchain + "/" + name
        if not os.path.exists(destination):
            shutil.copytree(path, destination)
        chdir(destination)
        
        configure(host, toolchain)
        com("make", "-j4")
        com("make", "install")
        restore_path()

def install_freetype():
    ft_orig = download_and_unpack(s.freetype_url)
    build_architectures(ft_orig, lambda host, toolchain:
        com("./configure", "--host=" + host, "--prefix=" + toolchain,
            "--without-png", "--without-harfbuzz",
            "--with-zlib=no",
            "--with-bzip2=no"))

def install_ogg():
    ogg_orig = download_and_unpack(s.ogg_url)
    build_architectures(ogg_orig, lambda host, toolchain:
        com("./configure", "--host=" + host, "--prefix=" + toolchain))

def install_vorbis():
    vorbis_orig = download_and_unpack(s.vorbis_url)
    
    # need to patch libvorbis 1.3.5 to work with clang on i386
    print("Patching libvorbis 1.3.5")
    b = open(vorbis_orig + "/configure").read()
    b = b.replace("-mno-ieee-fp", "")
    open(vorbis_orig + "/configure", "w").write(b)

    build_architectures(vorbis_orig, lambda host, toolchain:
        com("./configure", "--host=" + host, "--prefix=" + toolchain))

def build_allegro():
    for arch in s.architectures:
        print("Building Allegro for", arch)
        host, toolchain = setup_host(arch)
        build = args.path + "/build-android-" + arch
        if args.debug:
            build += "-debug"
        shutil.rmtree(build, ignore_errors = True)
        makedirs(build)
        chdir(build)

        # clang for arm crashes :(
        copy(args.allegro + "/cmake/Toolchain-android.cmake", "toolchain.cmake")
        if arch in ["armeabi", "armeabi-v7a"]:
            replace("toolchain.cmake", "clang++", "g++")
            replace("toolchain.cmake", "clang", "gcc")

        extra = None
        if arch == "armeabi":
            extra = "-DWANT_ANDROID_LEGACY=on"

        debug = "Release"
        if args.debug:
            debug = "Debug"
        com("cmake", args.allegro, "-DCMAKE_TOOLCHAIN_FILE=toolchain.cmake",
            "-DARM_TARGETS=" + arch,
            "-DCMAKE_BUILD_TYPE=" + debug,
            "-DANDROID_TARGET=android-26",
            extra,
            "-DWANT_DEMO=off",
            "-DWANT_EXAMPLES=off",
            "-DWANT_TESTS=off",
            "-DWANT_DOCS=off",
            "-DPKG_CONFIG_EXECUTABLE=/usr/bin/pkg-config",
            "-DOGG_LIBRARY=" + toolchain + "/lib/libogg.a",
            "-DOGG_INCLUDE_DIR=" + toolchain + "/include",
            "-DVORBIS_LIBRARY=" + toolchain + "/lib/libvorbis.a",
            "-DVORBISFILE_LIBRARY=" + toolchain + "/lib/libvorbisfile.a",
            "-DVORBIS_INCLUDE_DIR=" + toolchain + "/include",
            "-DSUPPORT_VORBIS=true",
            "-DFREETYPE_LIBRARY=" + toolchain + "/lib/libfreetype.a",
            "-DFREETYPE_INCLUDE_DIRS=" + toolchain + "/include;" + toolchain + "/include/freetype2",
            )
            
        com("make", "-j4", "VERBOSE=1")
        # Get rid of previously installed files, so for example we get
        # no debug libaries in a release build.
        rm(toolchain + "/user/" + arch + "/lib/liballegro*")
        com("make", "install")
        
        restore_path()

def build_aar():
    shutil.rmtree(args.path + "/gradle_project", ignore_errors = True)
    copy(args.allegro + "/android/gradle_project", args.path + "/gradle_project")
    
    allegro5 = args.path + "/gradle_project/allegro"

    for arch in s.architectures:
        toolchain = args.path + "/toolchain-" + arch
        install = toolchain + "/user/" + arch
        makedirs(allegro5 + "/src/main/jniLibs")
        copy(install + "/lib", allegro5 + "/src/main/jniLibs/" + arch)
        makedirs(allegro5 + "/src/main/assets/jniIncludes/" + arch)
        copy(install + "/include",
            allegro5 + "/src/main/assets/jniIncludes/" + arch + "/")
    write(allegro5 + "/src/main/assets/jniIncludes/allegro.cmake",
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
    set(path ${base}/${JNI_FOLDER}/${ABI}/lib${NAME})
    if(EXISTS "${path}-debug.so")
        set(LIB_${UNAME} ${path}-debug.so)
    elseif(EXISTS "${path}.so")
        set(LIB_${UNAME} ${path}.so)
    else()
        message(SEND_ERROR "${path}.so does not exist")
    endif()
    target_link_libraries(${NATIVE_LIB} ${LIB_${UNAME}})
endmacro()

include_directories(${base}/${ABI}/include)
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
        jcenter()
        google()
    }
    dependencies {
        classpath 'com.android.tools.build:gradle:2.3.3'
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
    compileSdkVersion 26
    buildToolsVersion "«build_tools_version»"
    defaultConfig {
        minSdkVersion 15
        targetSdkVersion 26
        versionCode 1
        versionName "«version»"
    }
}
dependencies {
    compile 'com.android.support:appcompat-v7:25.3.1'
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
    com("./gradlew", "bintrayUpload")

if __name__ == "__main__":
    main()
