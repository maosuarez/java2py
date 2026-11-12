import java.util.*;

public class Graphs {
    static class Edge implements Comparable<Edge> {
        final int to;
        final int weight;

        Edge(int to, int weight) {
            this.to = to;
            this.weight = weight;
        }

        @Override
        public int compareTo(Edge o) {
            return Integer.compare(weight, o.weight);
        }
    }

    static class Graph {
        private final int n;
        private final List<List<Edge>> adj = new ArrayList<>();

        Graph(int n) {
            this.n = n;
            for (int i = 0; i < n; i++) adj.add(new ArrayList<>());
        }

        void addEdge(int u, int v, int w) {
            adj.get(u).add(new Edge(v, w));
            adj.get(v).add(new Edge(u, w));
        }

        int[] dijkstra(int src) {
            int[] dist = new int[n];
            Arrays.fill(dist, Integer.MAX_VALUE);
            dist[src] = 0;
            PriorityQueue<Edge> pq = new PriorityQueue<>();
            pq.add(new Edge(src, 0));
            while (!pq.isEmpty()) {
                Edge cur = pq.poll();
                if (cur.weight > dist[cur.to]) continue;
                for (Edge e : adj.get(cur.to)) {
                    int nd = dist[cur.to] + e.weight;
                    if (nd < dist[e.to]) {
                        dist[e.to] = nd;
                        pq.add(new Edge(e.to, nd));
                    }
                }
            }
            return dist;
        }

        boolean hasPath(int a, int b) {
            boolean[] seen = new boolean[n];
            return dfs(a, b, seen);
        }

        private boolean dfs(int u, int target, boolean[] seen) {
            if (u == target) return true;
            seen[u] = true;
            for (Edge e : adj.get(u)) {
                if (!seen[e.to] && dfs(e.to, target, seen)) return true;
            }
            return false;
        }
    }

    static class UnionFind {
        int[] parent, rank;
        int count;

        UnionFind(int n) {
            parent = new int[n];
            rank = new int[n];
            count = n;
            for (int i = 0; i < n; i++) parent[i] = i;
        }

        int find(int x) {
            while (parent[x] != x) {
                parent[x] = parent[parent[x]];
                x = parent[x];
            }
            return x;
        }

        boolean union(int a, int b) {
            int ra = find(a), rb = find(b);
            if (ra == rb) return false;
            if (rank[ra] < rank[rb]) { int t = ra; ra = rb; rb = t; }
            parent[rb] = ra;
            if (rank[ra] == rank[rb]) rank[ra]++;
            count--;
            return true;
        }
    }

    static List<Integer> topoSort(int n, int[][] edges) {
        List<List<Integer>> g = new ArrayList<>();
        int[] indeg = new int[n];
        for (int i = 0; i < n; i++) g.add(new ArrayList<>());
        for (int[] e : edges) { g.get(e[0]).add(e[1]); indeg[e[1]]++; }
        Deque<Integer> q = new ArrayDeque<>();
        for (int i = 0; i < n; i++) if (indeg[i] == 0) q.offer(i);
        List<Integer> order = new ArrayList<>();
        while (!q.isEmpty()) {
            int u = q.poll();
            order.add(u);
            for (int v : g.get(u)) if (--indeg[v] == 0) q.offer(v);
        }
        return order;
    }

    static int islands(char[][] grid) {
        int count = 0;
        for (int r = 0; r < grid.length; r++) {
            for (int c = 0; c < grid[0].length; c++) {
                if (grid[r][c] == '1') {
                    count++;
                    sink(grid, r, c);
                }
            }
        }
        return count;
    }

    static void sink(char[][] grid, int r, int c) {
        if (r < 0 || c < 0 || r >= grid.length || c >= grid[0].length || grid[r][c] != '1') return;
        grid[r][c] = '0';
        int[][] dirs = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
        for (int[] d : dirs) sink(grid, r + d[0], c + d[1]);
    }

    public static void main(String[] args) {
        Graph g = new Graph(6);
        g.addEdge(0, 1, 7); g.addEdge(0, 2, 9); g.addEdge(0, 5, 14);
        g.addEdge(1, 2, 10); g.addEdge(1, 3, 15); g.addEdge(2, 3, 11);
        g.addEdge(2, 5, 2); g.addEdge(3, 4, 6);
        System.out.println(Arrays.toString(g.dijkstra(0)));
        System.out.println(g.hasPath(0, 4));

        UnionFind uf = new UnionFind(5);
        System.out.println(uf.union(0, 1) + " " + uf.union(1, 0) + " " + uf.union(3, 4) + " " + uf.count + " " + (uf.find(0) == uf.find(1)));

        System.out.println(topoSort(6, new int[][]{{5, 2}, {5, 0}, {4, 0}, {4, 1}, {2, 3}, {3, 1}}));

        char[][] grid = {
            "11000".toCharArray(),
            "11000".toCharArray(),
            "00100".toCharArray(),
            "00011".toCharArray()
        };
        System.out.println(islands(grid));
    }
}
