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
    jdk_url = "http://download.oracle.com/otn-pub/java/jdk/8u102-b14/jdk-8u102-linux-x64.tar.gz"
    sdk_tgz_url = "https://dl.google.com/android/android-sdk_r24.4.1-linux.tgz"
    ndk_zip_url = "https://dl.google.com/android/repository/android-ndk-r12b-linux-x86_64.zip"
    min_api = {
        "armeabi-v7a" : "15",
        "x86" : "15",
        "x86_64" : "21",
        "arm64-v8a" : "21",
        "mips" : "15",
        "mips64" : "21"}
    architectures = ["armeabi-v7a", "x86", "x86_64", "arm64-v8a", "mips", "mips64"]
    freetype_url = "http://download.savannah.gnu.org/releases/freetype/freetype-2.7.tar.bz2"
    ogg_url = "http://downloads.xiph.org/releases/ogg/libogg-1.3.2.tar.xz"
    vorbis_url = "http://downloads.xiph.org/releases/vorbis/libvorbis-1.3.5.tar.xz"
    
s = Settings()

def main():
    global args
    p = argparse.ArgumentParser()
    p.add_argument("-i", "--no-install", action = "store_true")
    p.add_argument("-b", "--no-build", action = "store_true")
    p.add_argument("-d", "--no-dist", action = "store_true")
    p.add_argument("-a", "--allegro", help = "path to allegro")
    p.add_argument("-p", "--path", help = "path to install to, by default current directory")
    p.add_argument("-A", "--arch", help = "comma separated list of architectures, by default all are built")
    args = p.parse_args()
    if not args.path:
        args.path = os.getcwd()
    s.log = open(args.path + "/install_android.log", "w")

    if args.arch:
        s.architectures = args.arch.split(",")
    s.sdk = download_and_unpack(s.sdk_tgz_url)
    s.ndk = download_and_unpack(s.ndk_zip_url)
    setup_jdk()
    
    if not args.no_install:
        install_sdk()
        install_ndk()
        install_freetype()
        install_ogg()
        install_vorbis()
        
    if not args.no_build:
        if not args.allegro:
            print("Need -a option to build!")
            return
        build_allegro()

    if not args.no_dist:
        build_aar()

def com(*args, input = None):
    args = [x for x in args if x is not None]
    print(" ".join(args))
    s.log.write(" ".join(args) + "\n")
    try:
        r = subprocess.run(args, check = True, input = input,
            stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        r = e
        sys.stderr.write(" ______\n")
        sys.stderr.write("/FAILED\\\n")
        sys.stderr.write("´`´`´`´`\n")
        s.log.write("FAILED\n")
    s.log.write(r.stdout.decode("utf8") + "\n")
    

def makedirs(name):
    s.log.write("mkdir -p " + name + "\n")
    print("mkdir -p " + name)
    os.makedirs(name, exist_ok = True)

def chdir(name):
    s.log.write("cd " + name + "\n")
    print("cd " + name)
    os.chdir(name)

def write(name, contents):
    print("create", name)
    open(name, "w").write(contents.strip() + "\n")

def copy(source, destination):
    com("cp", "-r", source, destination)

def replace(name, what, whatwith):
    print("edit", name)
    x = open(name, "r").read()
    x = x.replace(what, whatwith)
    open(name, "w").write(x)

def download(url, path):
    if not os.path.exists(path):
        print("Downloading", url)

        req = urllib.request.Request(url)
        req.add_header("Cookie", "oraclelicense=accept-securebackup-cookie")
        r = urllib.request.urlopen(req)
        with open(path + ".part", "wb") as f:
            f.write(r.read())
        os.rename(path + ".part", path)

def download_and_unpack(url):
    print("Checking", url)
    slash = url.rfind("/")
    name = args.path + "/" + url[slash + 1:]
    download(url, name)

    dot = name.rfind(".")
    folder = name[:dot]
    if folder.endswith(".tar"):
        folder = folder[:-4]
    if not os.path.exists(folder):
        shutil.rmtree(folder + ".part", ignore_errors = True)
        os.mkdir(folder + ".part")

        print("Unpacking", name)
        if zipfile.is_zipfile(name):
            # doesn't preserve permissions in some python versions
            #with zipfile.ZipFile(name) as z:
            #    z.extractall(folder + ".part")
            com("unzip", "-d", folder + ".part", name, "-q")
        else:
            tarfile.open(name).extractall(folder + ".part")

        for sub in glob.glob(folder + ".part/*"):
            if os.path.isdir(sub):
                shutil.move(sub, folder)
                break
        os.rmdir(folder + ".part")

    return folder

def setup_jdk():
    s.jdk = download_and_unpack(s.jdk_url)
    set_var("JAVA_HOME", s.jdk)

def install_sdk():
    components = [
        "platform-tools",
        "build-tools-24.0.2",
        "android-24",
        "extra-android-m2repository"
        ]
    android = s.sdk + "/tools/android"
    for component in components:
        com(android, "update", "sdk", "-u", "-a", "-t", component,
            input = b"y\n")

def install_ndk():
    for arch in s.architectures:
        toolchain = args.path + "/toolchain-" + arch
        if os.path.exists(toolchain):
            continue
        print("Creating toolchain for", arch)
        arch2 = arch
        if arch2 == "armeabi-v7a":
            arch2 = "arm"
        if arch2 == "arm64-v8a":
            arch2 = "arm64"
        com("python", s.ndk + "/build/tools/make_standalone_toolchain.py",
            "--arch", arch2, "--api", s.min_api[arch],
            "--install-dir", toolchain)
        # hack because cmake fails to find the 64-bit libs otherwise
        if arch == "mips64":
            com("mv", toolchain + "/sysroot/usr/lib", toolchain + "/sysroot/usr/lib-backup32")
            copy(toolchain + "/sysroot/usr/lib64", toolchain + "/sysroot/usr/lib")

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
    if arch == "armeabi-v7a":
        host = "arm-linux-androideabi"
    if arch == "arm64-v8a":
        host = "aarch64-linux-android"
    if arch == "mips":
        host = arch + "el-linux-android"
    if arch == "mips64":
        host = arch + "el-linux-android"

    set_var("ANDROID_NDK_ROOT", s.ndk)
    set_var("ANDROID_NDK_TOOLCHAIN_ROOT", toolchain)
    set_var("PKG_CONFIG_LIBDIR", toolchain + "/lib")
    backup_path()
    add_path(s.ndk)
    add_path(s.sdk + "/tools")
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
            "--without-png", "--without-harfbuzz"))

def install_ogg():
    ogg_orig = download_and_unpack(s.ogg_url)
    build_architectures(ogg_orig, lambda host, toolchain:
        com("./configure", "--host=" + host, "--prefix=" + toolchain))

def install_vorbis():
    vorbis_orig = download_and_unpack(s.vorbis_url)
    build_architectures(vorbis_orig, lambda host, toolchain:
        com("./configure", "--host=" + host, "--prefix=" + toolchain))

def build_allegro():
    for arch in s.architectures:
        print("Building Allegro for", arch)
        host, toolchain = setup_host(arch)
        build = args.path + "/build-android-" + arch
        makedirs(build)
        chdir(build)

        com("cmake", args.allegro, "-DCMAKE_TOOLCHAIN_FILE=" +
            args.allegro + "/cmake/Toolchain-android.cmake",
            "-DARM_TARGETS=" + arch,
            "-DCMAKE_BUILD_TYPE=Release",
            "-DANDROID_TARGET=android-24",
            "-DWANT_DEMO=off",
            "-DWANT_EXAMPLES=off",
            "-DWANT_TESTS=off",
            "-DWANT_DOCS=off",
            "-DPKG_CONFIG_EXECUTABLE=/usr/bin/pkg-config",
            "-DOGG_LIBRARY=" + toolchain + "/lib/libogg.a",
            "-DOGG_INCLUDE_DIR=" + toolchain + "/include",
            "-DVORBIS_LIBRARY=" + toolchain + "/lib/libvorbis.a",
            "-DVORBIS_INCLUDE_DIR=" + toolchain + "/include",
            "-DSUPPORT_VORBIS=true",
            "-DFREETYPE_LIBRARY=" + toolchain + "/lib/libfreetype.a",
            "-DFREETYPE_INCLUDE_DIRS=" + toolchain + "/include;" + toolchain + "/include/freetype2",
            )
        com("make", "-j4")
        com("make", "install")
        
        restore_path()

def build_aar():
    shutil.rmtree(args.path + "/gradle", ignore_errors = True)
    allegro5 = args.path + "/gradle/allegro5"
    shutil.rmtree(allegro5 + "/src", ignore_errors = True)
    makedirs(allegro5 + "/src/main/java/org/liballeg")
    copy(args.allegro + "/android/allegro_activity/src",
        allegro5 + "/src/main/java/org/liballeg/android")
    copy(s.sdk + "/tools/templates/gradle/wrapper/gradle",
        args.path + "/gradle/")
    copy(s.sdk + "/tools/templates/gradle/wrapper/gradlew",
        args.path + "/gradle/")
    replace(args.path + "/gradle/gradle/wrapper/gradle-wrapper.properties",
        "gradle-1.12-all.zip", "gradle-2.14.1-all.zip")
    for arch in s.architectures:
        toolchain = args.path + "/toolchain-" + arch
        install = toolchain + "/user/" + arch
        makedirs(allegro5 + "/src/main/assets/" + arch)
        copy(install + "/include",
            allegro5 + "/src/main/assets/" + arch + "/")
        makedirs(allegro5 + "/src/main/jniLibs")
        copy(install + "/lib", allegro5 + "/src/main/jniLibs/" + arch)
    write(allegro5 + "/src/main/AndroidManifest.xml", """
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="org.liballeg.android">
    <application android:allowBackup="true" android:label="Allegro 5"
        android:supportsRtl="true">
    </application>
</manifest>
""".lstrip())
    write(args.path + "/gradle/gradle.properties", """
org.gradle.java.home={}
""".format(s.jdk))
    write(args.path + "/gradle/local.properties", """
ndk.dir={}
sdk.dir={}
""".format(s.ndk, s.sdk))
    write(args.path + "/gradle/build.gradle", """
buildscript {
    repositories {
        jcenter()
    }
    dependencies {
        classpath 'com.android.tools.build:gradle:2.2.0'
    }
}
""")
    write(allegro5 + "/build.gradle", """
apply plugin: 'com.android.library'

android {
    compileSdkVersion 24
    buildToolsVersion "24.0.2"
    defaultConfig {
        minSdkVersion 15
        targetSdkVersion 24
        versionCode 1
        versionName "1.0"
    }
}
dependencies {
    compile fileTree(include: ['*.jar'], dir: 'libs')
    compile 'com.android.support:appcompat-v7:24.2.1'
}
""")
    write(args.path + "/gradle/settings.gradle", "include ':allegro5'")

if __name__ == "__main__":
    main()
