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
 compile 'org.liballeg:allegro5-release:5.2.2.0'
 ```
 
3. In your CMakeLists.txt, add this to the end:

 ```
 set(NATIVE_LIB native-lib)
 include(build/intermediates/exploded-aar/org.liballeg/allegro5-release/5.2.2.0/assets/allegro.cmake)
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

5. Replace app/src/main/native-lib.cpp with your game's C/C++ code, using Allegro. Use app/CMakeLists.txt to list all of your C/C++ source files and extra dependencies. Hit Run in Android Studio and it will
deploy and run your Allegro game on the emulator or actual devices. Build an .apk and upload it to the
store and it will just work!
