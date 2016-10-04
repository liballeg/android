This provides a script which will download the Linux Android SDK and builds Allegro for you.

This is work in progress, at the very least need to support updating, right now always have to start over

1. Create a new Android Studio NDK project

 Android Studio will create these files for you:

 * app/src/main/java/.../MainActivity.java
 * app/src/main/cpp/native-lib.cpp
 * app/build.gradle
 * app/CMakeLists.txt

2. In your app/build.gradle, inside of dependencies {}, add this:

 ```
 compile 'org.liballeg:allegro5-release:1.0.0'
 ```
 
3. In your CMakeLists.txt, add this to the end:

 ```
 set(NATIVE_LIB native-lib)
 include(build/intermediates/exploded-aar/allegro5-release/assets/allegro.cmake)
 ```

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

5. Edit your C/C++ code to use Allegro and use CMakeLists.txt for the list of source
files and extra dependencies. Hit Run in Android Studio and it will
deploy and run your Allegro game on the emulator or actual devices. Build an .apk and upload it to the
store and it will just work!

