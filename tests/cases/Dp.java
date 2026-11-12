import java.util.*;

public class Dp {
    static Map<Integer, Long> memo = new HashMap<>();
    static final int MOD = 1_000_000_007;
    static int calls = 0;

    static long fib(int n) {
        calls++;
        if (n <= 1) return n;
        if (memo.containsKey(n)) return memo.get(n);
        long v = fib(n - 1) + fib(n - 2);
        memo.put(n, v);
        return v;
    }

    static int knapsack(int[] w, int[] v, int cap) {
        int n = w.length;
        int[][] dp = new int[n + 1][cap + 1];
        for (int i = 1; i <= n; i++) {
            for (int c = 0; c <= cap; c++) {
                dp[i][c] = dp[i - 1][c];
                if (w[i - 1] <= c) {
                    dp[i][c] = Math.max(dp[i][c], dp[i - 1][c - w[i - 1]] + v[i - 1]);
                }
            }
        }
        return dp[n][cap];
    }

    static int lcs(String a, String b) {
        int[][] dp = new int[a.length() + 1][b.length() + 1];
        for (int i = 1; i <= a.length(); i++)
            for (int j = 1; j <= b.length(); j++)
                if (a.charAt(i - 1) == b.charAt(j - 1)) dp[i][j] = dp[i - 1][j - 1] + 1;
                else dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
        return dp[a.length()][b.length()];
    }

    static int coinChange(int[] coins, int amount) {
        int[] dp = new int[amount + 1];
        Arrays.fill(dp, amount + 1);
        dp[0] = 0;
        for (int a = 1; a <= amount; a++)
            for (int coin : coins)
                if (coin <= a) dp[a] = Math.min(dp[a], dp[a - coin] + 1);
        return dp[amount] > amount ? -1 : dp[amount];
    }

    static int lis(int[] nums) {
        int[] dp = new int[nums.length];
        int best = 0;
        for (int i = 0; i < nums.length; i++) {
            dp[i] = 1;
            for (int j = 0; j < i; j++)
                if (nums[j] < nums[i] && dp[j] + 1 > dp[i]) dp[i] = dp[j] + 1;
            best = Math.max(best, dp[i]);
        }
        return best;
    }

    static void permute(List<Integer> cur, boolean[] used, int[] nums, List<List<Integer>> out) {
        if (cur.size() == nums.length) {
            out.add(new ArrayList<>(cur));
            return;
        }
        for (int i = 0; i < nums.length; i++) {
            if (used[i]) continue;
            used[i] = true;
            cur.add(nums[i]);
            permute(cur, used, nums, out);
            cur.remove(cur.size() - 1);
            used[i] = false;
        }
    }

    static boolean solveQueens(int row, int n, int[] cols) {
        if (row == n) return true;
        for (int c = 0; c < n; c++) {
            boolean ok = true;
            for (int r = 0; r < row; r++) {
                if (cols[r] == c || Math.abs(cols[r] - c) == row - r) { ok = false; break; }
            }
            if (!ok) continue;
            cols[row] = c;
            if (solveQueens(row + 1, n, cols)) return true;
        }
        return false;
    }

    static long power(long base, int exp) {
        long result = 1;
        while (exp > 0) {
            if ((exp & 1) == 1) result = result * base % MOD;
            base = base * base % MOD;
            exp >>= 1;
        }
        return result;
    }

    static int gcd(int a, int b) { return b == 0 ? a : gcd(b, a % b); }

    static List<Integer> primes(int n) {
        boolean[] composite = new boolean[n + 1];
        List<Integer> out = new ArrayList<>();
        for (int i = 2; i <= n; i++) {
            if (composite[i]) continue;
            out.add(i);
            for (long j = (long) i * i; j <= n; j += i) composite[(int) j] = true;
        }
        return out;
    }

    static void hanoi(int n, char from, char to, char aux, List<String> moves) {
        if (n == 0) return;
        hanoi(n - 1, from, aux, to, moves);
        moves.add(from + "->" + to);
        hanoi(n - 1, aux, to, from, moves);
    }

    public static void main(String[] args) {
        System.out.println(fib(50) + " calls=" + calls);
        System.out.println(knapsack(new int[]{1, 3, 4, 5}, new int[]{1, 4, 5, 7}, 7));
        System.out.println(lcs("AGGTAB", "GXTXAYB") + " " + coinChange(new int[]{1, 2, 5}, 11) + " " + coinChange(new int[]{2}, 3));
        System.out.println(lis(new int[]{10, 9, 2, 5, 3, 7, 101, 18}));
        List<List<Integer>> perms = new ArrayList<>();
        permute(new ArrayList<>(), new boolean[3], new int[]{1, 2, 3}, perms);
        System.out.println(perms.size() + " " + perms.get(3));
        int[] cols = new int[6];
        System.out.println(solveQueens(0, 6, cols) + " " + Arrays.toString(cols));
        System.out.println(power(2, 100) + " " + gcd(84, 36) + " " + primes(30));
        List<String> moves = new ArrayList<>();
        hanoi(3, 'A', 'C', 'B', moves);
        System.out.println(moves.size() + " " + moves.get(0) + " " + String.join(" ", moves));
        int i = 0, total = 0;
        while (i++ < 5) total += i;
        int j = 10;
        while (--j > 5) total += j;
        for (int a = 0, b = 10; a < b; a++, b--) {
            if (a == 2) continue;
            total += b - a;
        }
        System.out.println(total + " " + i + " " + j);
        outer:
        for (int x = 0; x < 3; x++) {
            for (int y = 0; y < 3; y++) {
                if (y == 2) continue;
                total += x * y;
            }
        }
        double[] vals = {1, 2.5, 4};
        double s = 0;
        for (double d : vals) s += d;
        float f = 3;
        System.out.println(total + " " + s / vals.length + " " + f + " " + (5 + 3) / 2 + " " + (int) 3.99 + " " + Math.round(2.5) + " " + 10 % 3);
    }
}
