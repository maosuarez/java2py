import java.util.Iterator;
import java.util.NoSuchElementException;

public class Sedgewick {
    /** Bolsa/pila generica al estilo de "Algorithms" (Sedgewick). */
    static class LinkedStack<Item> implements Iterable<Item> {
        private Node first;     // tope de la pila
        private int n;          // numero de elementos

        private class Node {
            Item item;
            Node next;
        }

        public boolean isEmpty() { return first == null; }

        public int size() { return n; }

        public void push(Item item) {
            Node oldfirst = first;
            first = new Node();
            first.item = item;
            first.next = oldfirst;
            n++;
        }

        public Item pop() {
            if (isEmpty()) throw new NoSuchElementException("Stack underflow");
            Item item = first.item;
            first = first.next;
            n--;
            return item;
        }

        public Iterator<Item> iterator() { return new ListIterator(); }

        private class ListIterator implements Iterator<Item> {
            private Node current = first;

            public boolean hasNext() { return current != null; }

            public Item next() {
                Item item = current.item;
                current = current.next;
                return item;
            }
        }
    }

    static class Counter {
        private final String name;
        private int count;
        private static int instances;

        Counter(String name) { this.name = name; instances++; }

        void increment() { count++; }
        int tally() { return count; }
        public String toString() { return count + " " + name; }

        class Resetter {
            int resets;
            Resetter() { resets = 0; }
            Resetter(int start) { this(); resets = start; }
            void reset() { count = 0; resets++; increment(); }
        }

        Resetter resetter() { return new Resetter(10); }
    }

    static <T extends Comparable<T>> void sort(T[] a) {
        for (int i = 1; i < a.length; i++) {
            for (int j = i; j > 0 && a[j].compareTo(a[j - 1]) < 0; j--) {
                T t = a[j]; a[j] = a[j - 1]; a[j - 1] = t;
            }
        }
    }

    static <T extends Comparable<T>> T maxOf(T[] a) {
        T best = a[0];
        for (T x : a) if (x.compareTo(best) > 0) best = x;
        return best;
    }

    public static void main(String[] args) {
        LinkedStack<String> s = new LinkedStack<>();
        for (String w : "to be or not to be".split(" ")) s.push(w);
        StringBuilder sb = new StringBuilder();
        for (String w : s) sb.append(w).append(' ');
        System.out.println(sb.toString().trim() + " (" + s.size() + ")");
        Iterator<String> it = s.iterator();
        int chars = 0;
        while (it.hasNext()) {
            String w = it.next();
            chars += w.length();
        }
        System.out.println(chars + " " + s.pop() + " " + s.pop() + " " + s.size() + " " + s.isEmpty());

        Counter c = new Counter("heads");
        c.increment(); c.increment();
        Counter.Resetter r = c.resetter();
        System.out.println(c + " / " + c.tally());
        r.reset();
        System.out.println(c + " resets=" + r.resets);

        String[] names = {"pear", "apple", "fig"};
        sort(names);
        Integer[] nums = {5, 3, 9, 1};
        sort(nums);
        System.out.println(String.join(",", names) + " " + nums[0] + nums[3] + " " + maxOf(names) + " " + maxOf(nums));
    }
}
