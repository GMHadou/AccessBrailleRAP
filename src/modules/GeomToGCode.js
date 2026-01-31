class GeomToGCode {
    constructor() {
        this.speed = 6000;
        // Page width along X in millimeters; keep default 75 if used elsewhere
        this.pageWidthX = 75;
        // Left margin from printer parameters (mm)
        this.leftMarginX = 0;
        // whether to invert Y axis (flip sign of Y moves)
        this.invertY = false;
        // Whether to home to max (kept for compatibility but not used in simplified flow)
        this.homeToMax = false;
        // accumulated gcode as string
        this.gcode = '';
    }

    MotorOff() {
        return 'M84;\r\n';
    }

    Home() {
        // Keep homing simple: run a quick regulation check, home X, then move to
        // the desired starting X (left margin) using a G0 command and declare X=0.
        let str = '';
        str += 'G90;\r\n';                    // absolute positioning
        str += 'M119;\r\n';                   // quick endstop report (regulate)
        str += 'G28 X;\r\n';                  // home X (mechanical)
        // Move to the initial print X position (left margin)
        str += 'G0 X' + this.leftMarginX.toFixed(2) + ';\r\n';
        // Declare current position as X=0 (work coordinate starts at left margin)
        str += 'G92 X0;\r\n';
        // Home Y as before
        str += 'G28 Y;\r\n';
        return str;
    }

    setLeftMargin(margin) {
        const m = Number(margin);
        if (isNaN(m) || m < 0) {
            this.leftMarginX = 0;
            return;
        }
        // clamp to page width
        this.leftMarginX = Math.min(m, this.pageWidthX);
    }

    setInvertY(flag) {
        // accept boolean or truthy/falsy values
        this.invertY = (flag === true || flag === 1 || flag === '1' || flag === 'true');
    }

    setPageWidth(w) {
        const pw = Number(w);
        if (!isNaN(pw) && pw > 0) {
            this.pageWidthX = pw;
            // also clamp margin if needed
            this.leftMarginX = Math.min(this.leftMarginX, this.pageWidthX);
        }
    }

    gcodePosition(X, Y) {
        let code = '';
        if (X == null && Y == null) {
            throw new Error('Null position when moving');
        }
        if (X != null) {
            code += ' X' + X.toFixed(2);
        }
        if (Y != null) {
            code += ' Y' + Y.toFixed(2);
        }

        code += ';\r\n';
        return code;
    }

    gcodeResetPosition(X, Y) {
        return 'G92' + this.gcodePosition(X, Y);
    }

    SetSpeed(speed) {
        return 'G1 F' + speed + ';\r\n';
    }

    MoveTo(X, Y) {
        // Convert absolute geometry coordinates (which already include left margin)
        // into machine coordinates where X=0 is at the left margin.
        let adjX = X;
        if (adjX != null) adjX = (Number(adjX) - this.leftMarginX);

        let adjY = null;
        if (Y != null) {
            adjY = Number(Y);
            if (this.invertY) adjY = -adjY;
        }

        return 'G1' + this.gcodePosition(adjX, adjY);
    }

    PrintDot() {
        let s = 'M3 S155;\r\n';
        s += 'M3 S0;\r\n';
        return s;
    }

    GeomToGCode(pts) {
        this.gcode = '';
        this.gcode += this.Home();
        this.gcode += this.SetSpeed(this.speed);
        // Move to logical origin (left margin, top baseline)
        this.gcode += this.MoveTo(this.leftMarginX, 0);

        for (let p = 0; p < pts.length; p++) {
            this.gcode += this.MoveTo(pts[p].x, pts[p].y);
            this.gcode += this.PrintDot();
        }

        this.gcode += this.MoveTo(0, 300);
        this.gcode += this.MotorOff();
    }

    GetGcode() {
        return this.gcode;
    }
}

export default GeomToGCode;
