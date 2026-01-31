; Braille RAP Test Pattern
; Home axes
G28

; Move to start position
G90 ; Absolute positioning
G1 X10 Y10 Z5 F2000

; Lower head to emboss dot
G1 Z0 F500
G4 P200 ; dwell 200 ms
G1 Z5 F500

; Move a bit to the right and emboss another dot
G1 X15 Y10 F2000
G1 Z0 F500
G4 P200
G1 Z5 F500

; Move down one row (simulate Braille 2nd row)
G1 X10 Y15 F2000
G1 Z0 F500
G4 P200
G1 Z5 F500

; Finish
G1 X0 Y0 F3000
M84 ; disable motors
