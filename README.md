To use the Allegro Android binaries from Android Studio 2 or 3:

1. Create a new Android Studio NDK project
 * Use "Start a new Android Studio project" from the welcome dialog or File->New from the menu
 * Select C++ project (Or in AS 3.2 check the "Include C++ support" checkbox on the first dialog)
 * Leave minimum SDK at 15 on the second dialog
 * Leave the C++ settings at their defaults
 * Click "Finish"

  Android Studio will create these files in your new project's folder (among others):

 * app/src/main/java/.../MainActivity.java
 * app/src/main/cpp/native-lib.cpp
 * app/build.gradle
 * app/src/main/cpp/CMakeLists.txt

 Run your project, just to make sure everything works right in your
 Android Studio installation and with your emulator and/or test device.
 The test program will display a text which comes from the native
 library.

2. In your app/build.gradle, inside of dependencies {}, add this:

 ```
 implementation 'org.liballeg:allegro5-release:5.2.6.0A'
 ```
 
 or this for Android Studio 2:
 
 ```
 compile 'org.liballeg:allegro5-release:5.2.6.0A'
 ```
 
 In Android Studio in the "Android" view this file will be under "Gradle Scripts".
 
 (you can also use -debug instead of -release to use a debug version of Allegro)

 Sync your project (Tools-\>Android). This will make Android Studio download the .aar file from here:

 https://bintray.com/liballeg/maven
 
 If you prefer, you can remove the implementation/compile line and download the .aar
 yourself and open with any zip program. Then copy the .jar and .so files to where
 Android Studio can find them.

 Next install the Allegro headers:

 http://allegro5.org/android/5.2.6.0/allegro_jni_includes.zip

 And unzip anywhere, for this example I will put it inside the project folder, so
 it will end up as app/src/main/allegro\_jni\_includes.
 
3. In your CMakeLists.txt (under External Build Files in Android Studio), add this to the end and sync:

 ```
 set(NATIVE_LIB native-lib)
 set(JNI_FOLDER ${PROJECT_SOURCE_DIR}/../allegro_jni_includes) # or wherever you put it
 include(${JNI_FOLDER}/allegro.cmake)
 ```

4. Modify app/src/main/java/.../MainActivity.java like this:
 (Keep the original package name in the first line.)

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

 To test that everything works you can initially just paste the following code into the existing native-lib.cpp.
 It creates a display then fades it from red to yellow every second.

 ```c
  #include <allegro5/allegro5.h>

  int main(int argc, char **argv) {
      al_init();
      auto display = al_create_display(0, 0);
      auto queue = al_create_event_queue();
      auto timer = al_create_timer(1 / 60.0);
      auto redraw = true;
      al_register_event_source(queue, al_get_display_event_source(display));
      al_register_event_source(queue, al_get_timer_event_source(timer));
      al_start_timer(timer);
      while (true) {
          if (redraw) {
              al_clear_to_color(al_map_rgb_f(1, al_get_time() - (int)(al_get_time()), 0));
              al_flip_display();
              redraw = false;
          }
          ALLEGRO_EVENT event;
          al_wait_for_event(queue, &event);
          if (event.type == ALLEGRO_EVENT_TIMER) {
              redraw = true;
          }
      }
      return 0;
  }
```

6. Fine-tuning

* If you don't want to compile all the architectures for your game, you can do something like this in your app/build.gradle:
    ```
    buildTypes {
      debug { 
         ndk {
           abiFilters "armeabi-v7a""
         }
       }
    }
    ```
 * You will want to modify AndroidManifest.xml to have this attribute for the &lt;activity&gt; element or Allegro will crash:
    ```
    android:configChanges="orientation|keyboardHidden|screenLayout|uiMode|screenSize"
    ```
