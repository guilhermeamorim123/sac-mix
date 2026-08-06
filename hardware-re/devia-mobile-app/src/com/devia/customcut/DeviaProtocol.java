package com.devia.customcut;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Reconstructed from static analysis of com.icebartech.phonefilm_devia
 * (com.second.st_phonefilm, "Devia Custom Cut" app), PrintActivityCustom.smali.
 * Not yet validated against a real cut on real hardware -- only the
 * identification/handshake commands (RHVER/RPID/etc, see DeviaBluetoothLink)
 * have been confirmed against a live device this session.
 */
public class DeviaProtocol {

    // dots-per-mm scale factor baked into the wire protocol (confirmed: 0x42200000 = 40.0f)
    public static final int SCALE = 40;

    // fixed magic constant found hardcoded in the app; unknown meaning
    // (likely a job-format/protocol-version signature), reused verbatim.
    private static final String WSJP_MAGIC = "6240092912";

    private static final Map<Character, Character> DIGIT_CIPHER = new HashMap<>();
    static {
        DIGIT_CIPHER.put('0', '2');
        DIGIT_CIPHER.put('1', '0');
        DIGIT_CIPHER.put('2', '9');
        DIGIT_CIPHER.put('3', '7');
        DIGIT_CIPHER.put('4', '8');
        DIGIT_CIPHER.put('5', '6');
        DIGIT_CIPHER.put('6', '4');
        DIGIT_CIPHER.put('7', '3');
        DIGIT_CIPHER.put('8', '5');
        DIGIT_CIPHER.put('9', '1');
    }

    /** Applies the confirmed digit-substitution cipher, one character at a time. */
    static String cipherDigits(int n) {
        String s = Integer.toString(n);
        StringBuilder out = new StringBuilder(s.length());
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            Character mapped = DIGIT_CIPHER.get(c);
            out.append(mapped != null ? mapped : c);
        }
        return out.toString();
    }

    private static String pointToken(int x, int y) {
        return cipherDigits(x) + "," + cipherDigits(y);
    }

    /**
     * Generates one quarter-circle corner arc as a dense point cloud, exactly
     * matching PrintActivityCustom.b(FFFI): 179 points sampled at 0.5-degree
     * steps (angle 0.5..89.5 degrees), radius in already-scaled dots.
     *
     * quadrant selects which of the 4 rectangle corners this arc belongs to
     * -- TOP_RIGHT/TOP_LEFT/BOTTOM_LEFT/BOTTOM_RIGHT, matching the app's own
     * angle-code constants (90/180/270/360) so the call sites read the same
     * way the original does.
     */
    enum Corner { TOP_RIGHT, TOP_LEFT, BOTTOM_LEFT, BOTTOM_RIGHT }

    private static List<int[]> arcPoints(int radius, int centerX, int centerY, Corner corner) {
        List<int[]> points = new ArrayList<>();
        for (int step = 1; step < 180; step++) {
            double angleRad = Math.toRadians(step * 0.5);
            int dx = (int) Math.round(radius * Math.cos(angleRad));
            int dy = (int) Math.round(radius * Math.sin(angleRad));
            int x, y;
            switch (corner) {
                case TOP_RIGHT:
                    x = centerX + dx;
                    y = centerY - dy;
                    break;
                case TOP_LEFT:
                    x = centerX - dy;
                    y = centerY - dx;
                    break;
                case BOTTOM_LEFT:
                    x = centerX - dx;
                    y = centerY + dy;
                    break;
                default: // BOTTOM_RIGHT
                    x = centerX + dy;
                    y = centerY + dx;
                    break;
            }
            points.add(new int[]{x, y});
        }
        return points;
    }

    /**
     * Builds the raw (un-ciphered) point path for a rounded-rectangle outline,
     * in mm input, standard geometry (corner arc centers inset by radius from
     * each rectangle corner). This is the natural/standard way to draw a
     * rounded rect and matches every primitive confirmed from the app's own
     * code (arc math, point format, scale factor) -- but the exact traversal
     * order/starting corner used by the real app was not fully isolated from
     * PrintActivityCustom.a(FFF)'s notch-cutout-entangled logic, so treat this
     * as "should work" rather than "byte-identical to the real app," until
     * validated against a real machine.
     */
    static List<int[]> buildRoundedRectPath(float widthMm, float heightMm, float radiusMm) {
        int w = Math.round(widthMm * SCALE);
        int h = Math.round(heightMm * SCALE);
        int r = Math.round(radiusMm * SCALE);

        List<int[]> path = new ArrayList<>();
        // corner centers, inset by r from each of the 4 rectangle corners
        int cxLeft = r, cxRight = w - r;
        int cyTop = r, cyBottom = h - r;

        // start at top edge, just right of the top-left corner
        path.add(new int[]{cxLeft, 0});
        path.add(new int[]{cxRight, 0});
        path.addAll(arcPoints(r, cxRight, cyTop, Corner.TOP_RIGHT));
        path.add(new int[]{w, cyTop});
        path.add(new int[]{w, cyBottom});
        path.addAll(arcPoints(r, cxRight, cyBottom, Corner.BOTTOM_RIGHT));
        path.add(new int[]{cxRight, h});
        path.add(new int[]{cxLeft, h});
        path.addAll(arcPoints(r, cxLeft, cyBottom, Corner.BOTTOM_LEFT));
        path.add(new int[]{0, cyBottom});
        path.add(new int[]{0, cyTop});
        path.addAll(arcPoints(r, cxLeft, cyTop, Corner.TOP_LEFT));
        path.add(new int[]{cxLeft, 0});
        return path;
    }

    /**
     * Builds the full outbound cut-job command, confirmed byte-for-byte
     * structure from PrintActivityCustom.a(FFF):
     *   IN WSJP=<magic> U<x0>,<y0> D<x1>,<y1> ... D<xN>,<yN> U<0>,<0>
     * "IN" = HPGL Initialize, "U" = pen-up move (first point only),
     * "D" = pen-down cut (every subsequent point), closes with pen-up
     * to the (ciphered) origin. Every digit is passed through the
     * digit-substitution cipher.
     */
    public static String buildCutCommand(float widthMm, float heightMm, float radiusMm) {
        List<int[]> path = buildRoundedRectPath(widthMm, heightMm, radiusMm);
        StringBuilder cmd = new StringBuilder();
        cmd.append("IN WSJP=").append(WSJP_MAGIC).append(" ");
        for (int i = 0; i < path.size(); i++) {
            int[] p = path.get(i);
            cmd.append(i == 0 ? "U" : "D").append(pointToken(p[0], p[1])).append(" ");
        }
        cmd.append("U").append(pointToken(0, 0)).append(" ");
        return cmd.toString();
    }
}
