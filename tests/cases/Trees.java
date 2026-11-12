import java.util.*;

public class Trees {
    /** Nodo de un arbol binario de busqueda. */
    static class Node {
        int key;
        Node left, right;

        Node(int key) {
            this.key = key;
        }
    }

    static class BST {
        private Node root;
        private int size;

        public void insert(int key) {
            root = insert(root, key);
        }

        private Node insert(Node node, int key) {
            if (node == null) {
                size++;
                return new Node(key);
            }
            if (key < node.key) node.left = insert(node.left, key);
            else if (key > node.key) node.right = insert(node.right, key);
            return node;
        }

        public boolean contains(int key) {
            Node cur = root;
            while (cur != null) {
                if (key == cur.key) return true;
                cur = key < cur.key ? cur.left : cur.right;
            }
            return false;
        }

        public int height() { return height(root); }

        private int height(Node n) {
            return n == null ? 0 : 1 + Math.max(height(n.left), height(n.right));
        }

        public List<Integer> inorder() {
            List<Integer> out = new ArrayList<>();
            inorder(root, out);
            return out;
        }

        private void inorder(Node n, List<Integer> out) {
            if (n == null) return;
            inorder(n.left, out);
            out.add(n.key);
            inorder(n.right, out);
        }

        public List<List<Integer>> levels() {
            List<List<Integer>> result = new ArrayList<>();
            if (root == null) return result;
            Queue<Node> q = new LinkedList<>();
            q.add(root);
            while (!q.isEmpty()) {
                int n = q.size();
                List<Integer> level = new ArrayList<>();
                for (int i = 0; i < n; i++) {
                    Node cur = q.poll();
                    level.add(cur.key);
                    if (cur.left != null) q.add(cur.left);
                    if (cur.right != null) q.add(cur.right);
                }
                result.add(level);
            }
            return result;
        }

        public void delete(int key) { root = delete(root, key); }

        private Node delete(Node node, int key) {
            if (node == null) return null;
            if (key < node.key) {
                node.left = delete(node.left, key);
            } else if (key > node.key) {
                node.right = delete(node.right, key);
            } else {
                size--;
                if (node.left == null) return node.right;
                if (node.right == null) return node.left;
                Node min = node.right;
                while (min.left != null) min = min.left;
                node.key = min.key;
                size++;
                node.right = delete(node.right, min.key);
            }
            return node;
        }

        public int size() { return size; }

        public List<Integer> iterativeInorder() {
            List<Integer> out = new ArrayList<>();
            Deque<Node> stack = new ArrayDeque<>();
            Node cur = root;
            while (cur != null || !stack.isEmpty()) {
                while (cur != null) {
                    stack.push(cur);
                    cur = cur.left;
                }
                cur = stack.pop();
                out.add(cur.key);
                cur = cur.right;
            }
            return out;
        }
    }

    /** Monticulo minimo sobre un arreglo. */
    static class MinHeap {
        private int[] heap;
        private int size;

        MinHeap(int capacity) {
            heap = new int[capacity];
            size = 0;
        }

        private int parent(int i) { return (i - 1) / 2; }

        private void swap(int i, int j) {
            int t = heap[i];
            heap[i] = heap[j];
            heap[j] = t;
        }

        void add(int v) {
            if (size == heap.length) heap = Arrays.copyOf(heap, size * 2);
            heap[size] = v;
            int i = size++;
            while (i > 0 && heap[parent(i)] > heap[i]) {
                swap(i, parent(i));
                i = parent(i);
            }
        }

        int poll() {
            if (size == 0) throw new NoSuchElementException("heap vacio");
            int min = heap[0];
            heap[0] = heap[--size];
            int i = 0;
            while (true) {
                int l = 2 * i + 1, r = 2 * i + 2, smallest = i;
                if (l < size && heap[l] < heap[smallest]) smallest = l;
                if (r < size && heap[r] < heap[smallest]) smallest = r;
                if (smallest == i) break;
                swap(i, smallest);
                i = smallest;
            }
            return min;
        }

        boolean isEmpty() { return size == 0; }
    }

    public static void main(String[] args) {
        BST t = new BST();
        int[] keys = {50, 30, 70, 20, 40, 60, 80, 30};
        for (int k : keys) t.insert(k);
        System.out.println(t.inorder() + " size=" + t.size() + " h=" + t.height());
        System.out.println(t.contains(60) + " " + t.contains(65));
        System.out.println(t.levels());
        t.delete(50); t.delete(20); t.delete(999);
        System.out.println(t.iterativeInorder() + " size=" + t.size());

        MinHeap h = new MinHeap(2);
        for (int v : new int[]{9, 4, 7, 1, 8, 2}) h.add(v);
        StringBuilder sb = new StringBuilder();
        while (!h.isEmpty()) sb.append(h.poll()).append(" ");
        System.out.println(sb.toString().trim());
        try {
            h.poll();
        } catch (NoSuchElementException e) {
            System.out.println("vacio: " + e.getMessage());
        }
    }
}
