import java.util.*;

public class Collections1 {
    static boolean balanced(String s) {
        Stack<Character> stack = new Stack<>();
        for (char c : s.toCharArray()) {
            if (c == '(' || c == '[' || c == '{') {
                stack.push(c);
            } else {
                if (stack.isEmpty()) return false;
                char top = stack.pop();
                if ((c == ')' && top != '(') || (c == ']' && top != '[') || (c == '}' && top != '{'))
                    return false;
            }
        }
        return stack.isEmpty();
    }

    static List<Integer> bfs(List<List<Integer>> graph, int start) {
        List<Integer> order = new ArrayList<>();
        boolean[] visited = new boolean[graph.size()];
        Queue<Integer> queue = new LinkedList<>();
        queue.offer(start);
        visited[start] = true;
        while (!queue.isEmpty()) {
            int node = queue.poll();
            order.add(node);
            for (int next : graph.get(node)) {
                if (!visited[next]) {
                    visited[next] = true;
                    queue.add(next);
                }
            }
        }
        return order;
    }

    static void dfs(List<List<Integer>> graph, int node, Set<Integer> seen, List<Integer> out) {
        if (seen.contains(node)) return;
        seen.add(node);
        out.add(node);
        for (int next : graph.get(node)) dfs(graph, next, seen, out);
    }

    static int[] twoSum(int[] nums, int target) {
        Map<Integer, Integer> seen = new HashMap<>();
        for (int i = 0; i < nums.length; i++) {
            int need = target - nums[i];
            if (seen.containsKey(need)) return new int[]{seen.get(need), i};
            seen.put(nums[i], i);
        }
        return new int[0];
    }

    public static void main(String[] args) {
        System.out.println(balanced("{[()]}") + " " + balanced("([)]") + " " + balanced("(("));

        List<List<Integer>> graph = new ArrayList<>();
        for (int i = 0; i < 6; i++) graph.add(new ArrayList<>());
        int[][] edges = {{0, 1}, {0, 2}, {1, 3}, {2, 4}, {4, 5}};
        for (int[] e : edges) {
            graph.get(e[0]).add(e[1]);
            graph.get(e[1]).add(e[0]);
        }
        System.out.println("BFS: " + bfs(graph, 0));
        List<Integer> out = new ArrayList<>();
        dfs(graph, 0, new HashSet<>(), out);
        System.out.println("DFS: " + out);

        System.out.println(Arrays.toString(twoSum(new int[]{2, 7, 11, 15}, 26)));

        Map<String, Integer> freq = new HashMap<>();
        String text = "the quick brown fox jumps over the lazy dog the end";
        for (String w : text.split(" ")) {
            freq.put(w, freq.getOrDefault(w, 0) + 1);
        }
        List<String> keys = new ArrayList<>(freq.keySet());
        Collections.sort(keys);
        for (String k : keys) {
            if (freq.get(k) > 1) System.out.println(k + " -> " + freq.get(k));
        }
        int total = 0;
        for (Map.Entry<String, Integer> entry : freq.entrySet()) total += entry.getValue();
        System.out.println("total=" + total + " distinct=" + freq.size());

        PriorityQueue<Integer> pq = new PriorityQueue<>();
        for (int x : new int[]{5, 1, 8, 3, 2}) pq.add(x);
        StringBuilder sb = new StringBuilder();
        while (!pq.isEmpty()) sb.append(pq.poll()).append(' ');
        System.out.println(sb.toString().trim());

        Deque<Integer> dq = new ArrayDeque<>();
        dq.addFirst(1); dq.addLast(2); dq.addFirst(0);
        System.out.println(dq.peekFirst() + " " + dq.peekLast() + " " + dq.size());
        dq.pollFirst();
        System.out.println(dq.pop() + " " + dq.removeLast() + " " + dq.isEmpty());

        List<Integer> nums = new ArrayList<>(Arrays.asList(4, 8, 15, 16, 23, 42));
        nums.remove(0);
        nums.remove(Integer.valueOf(16));
        nums.set(0, 99);
        nums.add(1, 7);
        System.out.println(nums + " " + nums.contains(23) + " " + nums.indexOf(15) + " " + nums.get(nums.size() - 1));
        Collections.reverse(nums);
        System.out.println(nums + " max=" + Collections.max(nums));
        nums.sort((x, y) -> y - x);
        System.out.println(nums);

        Set<String> set = new HashSet<>();
        set.add("a"); set.add("b"); set.add("a");
        set.remove("b");
        System.out.println(set.size() + " " + set.contains("a"));
        Iterator<Integer> it = nums.iterator();
        System.out.println(it.next());
    }
}
