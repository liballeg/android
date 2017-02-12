To use the Allegro Android binaries from Android Studio 2.2:

1. Create a new Android Studio NDK project
 * File->New, check the "Include C++ support" checkbox on the first dialog
 * Pick "Empty Activity" and uncheck "Generate Layout" and "Backwards Compatibility"

  Android Studio will create these files in your new project's folder (among others):

 * app/src/main/java/.../MainActivity.java
 * app/src/main/cpp/native-lib.cpp
 * app/build.gradle
 * app/CMakeLists.txt

2. In your app/build.gradle, inside of dependencies {}, add this:

 ```
 compile 'org.liballeg:allegro5-release:5.2.3.0'
 ```
 (you can also use -debug instead of -release to use a debug version of Allegro)
 
 This will make Android Studio download the .aar file from here: https://bintray.com/liballeg/maven
 
 If you prefer, you can remove the "compile" line and download the .aar yourself and open with any zip program. Then copy the .jar and .so and .h files to where Android Studio can find them. Right now the .h files live in the "assets" folder which means they get distributed with the .apk, which wastes (a small bit of) space.
 
3. In your CMakeLists.txt, add this to the end:

 ```
 set(NATIVE_LIB native-lib)
 include(build/intermediates/exploded-aar/org.liballeg/allegro5-release/5.2.3.0/assets/allegro.cmake)
 ```
 Note: If you get an error message about allegro.cmake not being found (or just about cmake failing) - remove those two lines and do a rebuild (which will fail because it cannot find the Allegro headers). Then re-add those two lines and re-build again. This is because Android-Studio may not have unpacked the .aar file with allegro.cmake in it yet on the first run.

4. Modify app/src/main/java/.../MainActivity.java like this:

 ```
 import org.liballeg.android.AllegroActivity;
 public class MainActivity extends AllegroActivity {
     static {
         System.loadLibrary("allegro");
         System.loadLibrary("allegro_primitives");
         System.loadLibrary("allegro_image");
         System.loadLibrary("allegro_font");
         System.loadLibrary("allegro_ttf");
         System.loadLibrary("allegro_audio");
         System.loadLibrary("allegro_acodec");
         System.loadLibrary("allegro_color");
     }
     public MainActivity() {
         super("libnative-lib.so");
     }
 }
```
 (if you used the debug version above, the libraries will be called "allegro-debug" and so on)

5. Replace app/src/main/native-lib.cpp with your game's C/C++ code, using Allegro. Use app/CMakeLists.txt to list all of your C/C++ source files and extra dependencies. Hit Run in Android Studio and it will
deploy and run your Allegro game on the emulator or actual devices. Build an .apk and upload it to the
store and it will just work!

6. Fine-tuning

* You can move the assets/\*/include folders somewhere else if you don't want them to be in your final .apk
* If you don't want to compile all 7 architectures for your game, you can do something like this in your app/build.gradle:
    ```
    buildTypes {
      debug { 
         ndk {
           abiFilters "x86", "armeabi-v7a", "armeabi"
         }
       }
    }
    ```
