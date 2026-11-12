public class BusquedaBinaria {
    // Devuelve el índice de objetivo en arr (ordenado) o -1 si no está.
    static int buscar(int[] arr, int objetivo) {
        int lo = 0;
        int hi = arr.length - 1;
        while (lo <= hi) {
            int mid = lo + (hi - lo) / 2;
            if (arr[mid] == objetivo) {
                return mid;
            } else if (arr[mid] < objetivo) {
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }
        return -1;
    }

    // Primer índice cuyo valor es >= objetivo (lower bound).
    static int cotaInferior(int[] arr, int objetivo) {
        int lo = 0;
        int hi = arr.length;
        while (lo < hi) {
            int mid = lo + (hi - lo) / 2;
            if (arr[mid] < objetivo) {
                lo = mid + 1;
            } else {
                hi = mid;
            }
        }
        return lo;
    }

    public static void main(String[] args) {
        int[] datos = {2, 3, 5, 7, 11, 13, 17, 19};
        System.out.println("buscar 13 -> " + buscar(datos, 13));
        System.out.println("buscar 4 -> " + buscar(datos, 4));
        System.out.println("cotaInferior 4 -> " + cotaInferior(datos, 4));
        System.out.println("cotaInferior 20 -> " + cotaInferior(datos, 20));
    }
}
