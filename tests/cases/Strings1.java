public class Strings1 {
    static boolean isPalindrome(String s) {
        int i = 0, j = s.length() - 1;
        while (i < j) {
            if (s.charAt(i++) != s.charAt(j--)) return false;
        }
        return true;
    }

    static String reverse(String s) {
        return new StringBuilder(s).reverse().toString();
    }

    static boolean isAnagram(String a, String b) {
        if (a.length() != b.length()) return false;
        int[] count = new int[26];
        for (int i = 0; i < a.length(); i++) {
            count[a.charAt(i) - 'a']++;
            count[b.charAt(i) - 'a']--;
        }
        for (int c : count) if (c != 0) return false;
        return true;
    }

    static String caesar(String s, int shift) {
        StringBuilder sb = new StringBuilder();
        for (char c : s.toCharArray()) {
            if (Character.isUpperCase(c)) {
                sb.append((char) ('A' + (c - 'A' + shift) % 26));
            } else if (Character.isLowerCase(c)) {
                sb.append((char) ('a' + (c - 'a' + shift) % 26));
            } else {
                sb.append(c);
            }
        }
        return sb.toString();
    }

    static int vowels(String s) {
        int n = 0;
        for (int i = 0; i < s.length(); i++) {
            switch (Character.toLowerCase(s.charAt(i))) {
                case 'a': case 'e': case 'i': case 'o': case 'u':
                    n++;
                    break;
                default:
                    break;
            }
        }
        return n;
    }

    static String dayName(int d) {
        String name;
        switch (d) {
            case 1: name = "Mon"; break;
            case 2: name = "Tue"; break;
            case 6:
            case 7: name = "Weekend"; break;
            default: name = "Other";
        }
        return name;
    }

    static String grade(int score) {
        return switch (score / 10) {
            case 10, 9 -> "A";
            case 8 -> "B";
            default -> "F";
        };
    }

    static int atoi(String s) {
        int result = 0, sign = 1, i = 0;
        if (s.charAt(0) == '-') { sign = -1; i++; }
        for (; i < s.length(); i++) {
            char c = s.charAt(i);
            if (!Character.isDigit(c)) break;
            result = result * 10 + (c - '0');
        }
        return sign * result;
    }

    public static void main(String[] args) {
        System.out.println(isPalindrome("racecar") + " " + isPalindrome("java"));
        System.out.println(reverse("hello") + " " + isAnagram("listen", "silent"));
        System.out.println(caesar("Hello, World!", 3));
        System.out.println(vowels("Programming Language") + " " + dayName(2) + " " + dayName(7) + " " + dayName(4));
        System.out.println(grade(95) + grade(85) + grade(40));
        System.out.println(atoi("-1234x") + atoi("56"));
        String s = "  Data Structures  ";
        String t = s.trim();
        System.out.println(t.toUpperCase() + "|" + t.substring(5) + "|" + t.substring(0, 4) + "|" + t.indexOf("Str") + "|" + t.length());
        System.out.println(t.contains("ruct") + " " + t.startsWith("Data") + " " + t.equals("x") + " " + "b".compareTo("a") + " " + t.replace('a', '4'));
        String[] parts = "a,b,c".split(",");
        System.out.println(parts.length + " " + String.join("-", parts) + " " + parts[1].isEmpty());
        char[] chars = t.toCharArray();
        java.util.Arrays.sort(chars);
        System.out.println(new String(chars).trim() + " " + String.valueOf(chars).length());
        System.out.printf("%d items, %.2f avg, %s%n", 3, 2.5, "ok");
        System.out.println(String.format("%05d|%-5s|%5.1f", 42, "ab", 3.14159));
        int x = 7;
        x += 3; x *= 2; x -= 1; x /= 4; x %= 3;
        String msg = x > 0 ? "pos" : x == 0 ? "zero" : "neg";
        System.out.println(x + " " + msg + " " + (x << 3) + " " + (17 >> 2) + " " + (5 & 3) + " " + (5 | 3) + " " + (5 ^ 3));
        int count = 0;
        do { count++; } while (count < 5);
        long big = 1L << 40;
        double avg = (double) count / 2;
        System.out.println(count + " " + big + " " + avg + " " + Math.max(3, 9) + " " + Math.abs(-4) + " " + (int) Math.sqrt(50) + " " + Math.pow(2, 10) + " " + 7 / 2 + " " + 7 / 2.0 + " " + 7 % 3);
        char ch = 'a';
        ch++;
        int code = ch;
        System.out.println(ch + " " + code + " " + (char) (ch + 1) + " " + (int) 'A' + " " + Integer.parseInt("42") + Integer.MAX_VALUE);
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 3; i++) sb.append(i).append(",");
        sb.setLength(sb.length() - 1);
        sb.insert(0, "[").append("]");
        System.out.println(sb + " " + sb.length() + " " + sb.charAt(1));
        System.out.print("no newline");
        System.out.println();
        String nothing = null;
        System.out.println(nothing == null ? "nada" : nothing);
    }
}
