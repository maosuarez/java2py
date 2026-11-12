import java.util.NoSuchElementException;

public class UserDs {
    static class Stack<T> {
        private Object[] items = new Object[2];
        private int top = 0;

        void push(T item) {
            if (top == items.length) {
                Object[] bigger = new Object[items.length * 2];
                for (int i = 0; i < top; i++) bigger[i] = items[i];
                items = bigger;
            }
            items[top++] = item;
        }

        @SuppressWarnings("unchecked")
        T pop() {
            if (isEmpty()) throw new RuntimeException("Stack underflow");
            T item = (T) items[--top];
            items[top] = null;
            return item;
        }

        @SuppressWarnings("unchecked")
        T peek() { return (T) items[top - 1]; }

        boolean isEmpty() { return top == 0; }

        int size() { return top; }
    }

    static class Queue {
        private int[] data;
        private int head, tail, count;

        Queue(int capacity) { data = new int[capacity]; }

        boolean enqueue(int x) {
            if (count == data.length) return false;
            data[tail] = x;
            tail = (tail + 1) % data.length;
            count++;
            return true;
        }

        int dequeue() {
            if (count == 0) throw new NoSuchElementException();
            int x = data[head];
            head = (head + 1) % data.length;
            count--;
            return x;
        }

        int size() { return count; }
    }

    static class HashTable {
        private static class Entry {
            String key;
            int value;
            Entry next;

            Entry(String key, int value, Entry next) {
                this.key = key;
                this.value = value;
                this.next = next;
            }
        }

        private Entry[] buckets = new Entry[4];
        private int size;

        private int index(String key) {
            int h = 0;
            for (int i = 0; i < key.length(); i++) h = (h * 31 + key.charAt(i)) % 1000003;
            return h % buckets.length;
        }

        void put(String key, int value) {
            int i = index(key);
            for (Entry e = buckets[i]; e != null; e = e.next) {
                if (e.key.equals(key)) {
                    e.value = value;
                    return;
                }
            }
            buckets[i] = new Entry(key, value, buckets[i]);
            size++;
        }

        Integer get(String key) {
            Entry e = buckets[index(key)];
            while (e != null) {
                if (e.key.equals(key)) return e.value;
                e = e.next;
            }
            return null;
        }

        boolean remove(String key) {
            int i = index(key);
            Entry prev = null;
            Entry e = buckets[i];
            while (e != null) {
                if (e.key.equals(key)) {
                    if (prev == null) buckets[i] = e.next;
                    else prev.next = e.next;
                    size--;
                    return true;
                }
                prev = e;
                e = e.next;
            }
            return false;
        }

        int size() { return size; }
    }

    static class DoublyLinkedList {
        class Node {
            int val;
            Node prev, next;
            Node(int val) { this.val = val; }
        }

        Node head, tail;
        int length;

        void addFirst(int v) {
            Node n = new Node(v);
            if (head == null) { head = tail = n; }
            else { n.next = head; head.prev = n; head = n; }
            length++;
        }

        void addLast(int v) {
            Node n = new Node(v);
            if (tail == null) { head = tail = n; }
            else { tail.next = n; n.prev = tail; tail = n; }
            length++;
        }

        int removeFirst() {
            int v = head.val;
            head = head.next;
            if (head == null) tail = null; else head.prev = null;
            length--;
            return v;
        }

        String backwards() {
            String s = "";
            for (Node n = tail; n != null; n = n.prev) s += n.val + (n.prev != null ? "<" : "");
            return s;
        }
    }

    static int evalRpn(String[] tokens) {
        Stack<Integer> st = new Stack<>();
        for (String tok : tokens) {
            switch (tok) {
                case "+" -> st.push(st.pop() + st.pop());
                case "*" -> st.push(st.pop() * st.pop());
                case "-" -> {
                    int b = st.pop(), a = st.pop();
                    st.push(a - b);
                }
                default -> st.push(Integer.parseInt(tok));
            }
        }
        return st.pop();
    }

    public static void main(String[] args) {
        Stack<String> s = new Stack<>();
        s.push("a"); s.push("b"); s.push("c");
        System.out.println(s.pop() + s.peek() + s.size() + " " + s.isEmpty());
        System.out.println(evalRpn(new String[]{"2", "1", "+", "3", "*", "4", "-"}));

        Queue q = new Queue(3);
        q.enqueue(1); q.enqueue(2); q.enqueue(3);
        System.out.println(q.enqueue(4) + " " + q.dequeue() + " " + q.enqueue(5) + " " + q.dequeue() + q.dequeue() + q.dequeue() + " " + q.size());
        try {
            q.dequeue();
        } catch (NoSuchElementException e) {
            System.out.println("cola vacia");
        }

        HashTable t = new HashTable();
        String[] words = {"uno", "dos", "tres", "cuatro", "cinco", "dos"};
        for (int i = 0; i < words.length; i++) t.put(words[i], i);
        System.out.println(t.size() + " " + t.get("dos") + " " + t.get("seis") + " " + t.remove("tres") + " " + t.remove("tres") + " " + t.size());

        DoublyLinkedList d = new DoublyLinkedList();
        d.addLast(2); d.addLast(3); d.addFirst(1);
        System.out.println(d.backwards() + " " + d.removeFirst() + " " + d.length);
    }
}
