#import <Cocoa/Cocoa.h>
#include <unistd.h>
int main(int argc, char **argv) {
 @autoreleasepool {
  NSString *resources = [[NSBundle mainBundle] resourcePath];
  const char *paths[] = {"/opt/homebrew/bin/python3", "/usr/local/bin/python3", "/Library/Frameworks/Python.framework/Versions/Current/bin/python3", NULL};
  for (int i=0; paths[i]; i++) {
   if (access(paths[i], X_OK)==0) {
    chdir([resources fileSystemRepresentation]);
    setenv("PATH", "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin", 1);
    execl(paths[i], paths[i], [[resources stringByAppendingPathComponent:@"desktop.py"] fileSystemRepresentation], NULL);
   }
  }
  [NSApplication sharedApplication];
  NSAlert *alert = [[NSAlert alloc] init];
  alert.messageText = @"Install Python to open Cadenza";
  alert.informativeText = @"This macOS package needs Python 3.11+ with Tk, Node.js 22+, FFmpeg and Pygame. Install Python first; Cadenza will guide you through any remaining dependencies when you reopen it. Full instructions are included in DEPENDENCIES.txt.";
  [alert addButtonWithTitle:@"Install Python"];
  [alert addButtonWithTitle:@"Setup instructions"];
  [alert addButtonWithTitle:@"Close"];
  NSInteger choice=[alert runModal];
  if (choice==NSAlertFirstButtonReturn) [[NSWorkspace sharedWorkspace] openURL:[NSURL URLWithString:@"https://www.python.org/downloads/macos/"]];
  if (choice==NSAlertSecondButtonReturn) [[NSWorkspace sharedWorkspace] openURL:[NSURL fileURLWithPath:[resources stringByAppendingPathComponent:@"DEPENDENCIES.txt"]]];
 }
 return 1;
}
