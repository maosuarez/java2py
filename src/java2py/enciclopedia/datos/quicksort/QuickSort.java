public class QuickSort {
    static void ordenar(int[] a) {
        quicksort(a, 0, a.length - 1);
    }

    static void quicksort(int[] a, int lo, int hi) {
        if (lo >= hi) {
            return;
        }
        int p = particionar(a, lo, hi);
        quicksort(a, lo, p - 1);
        quicksort(a, p + 1, hi);
    }

    // Partición de Lomuto: el pivote es el último elemento.
    static int particionar(int[] a, int lo, int hi) {
        int pivote = a[hi];
        int i = lo;
        for (int j = lo; j < hi; j++) {
            if (a[j] < pivote) {
                intercambiar(a, i, j);
                i++;
            }
        }
        intercambiar(a, i, hi);
        return i;
    }

    static void intercambiar(int[] a, int i, int j) {
        int tmp = a[i];
        a[i] = a[j];
        a[j] = tmp;
    }

    static String mostrar(int[] a) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < a.length; i++) {
            if (i > 0) {
                sb.append(", ");
            }
            sb.append(a[i]);
        }
        return sb.append("]").toString();
    }

    public static void main(String[] args) {
        int[] datos = {9, 4, 7, 1, 8, 2, 6, 3, 5};
        System.out.println("antes:   " + mostrar(datos));
        ordenar(datos);
        System.out.println("despues: " + mostrar(datos));
    }
}
