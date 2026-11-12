public class MinHeap {
    private int[] a;
    private int n;

    MinHeap(int capacidad) {
        a = new int[capacidad];
        n = 0;
    }

    void insertar(int x) {
        a[n] = x;
        subir(n);
        n++;
    }

    int extraerMin() {
        int min = a[0];
        n--;
        a[0] = a[n];
        bajar(0);
        return min;
    }

    int minimo() {
        return a[0];
    }

    boolean estaVacio() {
        return n == 0;
    }

    private void subir(int i) {
        while (i > 0) {
            int padre = (i - 1) / 2;
            if (a[padre] <= a[i]) {
                break;
            }
            intercambiar(i, padre);
            i = padre;
        }
    }

    private void bajar(int i) {
        while (true) {
            int izq = 2 * i + 1;
            int der = 2 * i + 2;
            int menor = i;
            if (izq < n && a[izq] < a[menor]) {
                menor = izq;
            }
            if (der < n && a[der] < a[menor]) {
                menor = der;
            }
            if (menor == i) {
                return;
            }
            intercambiar(i, menor);
            i = menor;
        }
    }

    private void intercambiar(int i, int j) {
        int tmp = a[i];
        a[i] = a[j];
        a[j] = tmp;
    }

    public static void main(String[] args) {
        MinHeap h = new MinHeap(16);
        int[] valores = {15, 3, 9, 1, 12, 7, 4};
        for (int v : valores) {
            h.insertar(v);
        }
        System.out.println("minimo: " + h.minimo());
        StringBuilder sb = new StringBuilder();
        while (!h.estaVacio()) {
            sb.append(h.extraerMin()).append(" ");
        }
        System.out.println("en orden: " + sb.toString().trim());
    }
}
