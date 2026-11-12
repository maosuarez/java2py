import java.util.Arrays;

public class Sorting {
    static void bubbleSort(int[] arr) {
        int n = arr.length;
        for (int i = 0; i < n - 1; i++) {
            boolean swapped = false;
            for (int j = 0; j < n - i - 1; j++) {
                if (arr[j] > arr[j + 1]) {
                    int temp = arr[j];
                    arr[j] = arr[j + 1];
                    arr[j + 1] = temp;
                    swapped = true;
                }
            }
            if (!swapped) break;
        }
    }

    static void insertionSort(int[] arr) {
        for (int i = 1; i < arr.length; i++) {
            int key = arr[i];
            int j = i - 1;
            while (j >= 0 && arr[j] > key) {
                arr[j + 1] = arr[j];
                j--;
            }
            arr[j + 1] = key;
        }
    }

    static void selectionSort(int[] a) {
        for (int i = 0; i < a.length - 1; i++) {
            int min = i;
            for (int j = i + 1; j < a.length; j++)
                if (a[j] < a[min]) min = j;
            int t = a[min]; a[min] = a[i]; a[i] = t;
        }
    }

    static void mergeSort(int[] arr, int left, int right) {
        if (left >= right) return;
        int mid = left + (right - left) / 2;
        mergeSort(arr, left, mid);
        mergeSort(arr, mid + 1, right);
        merge(arr, left, mid, right);
    }

    private static void merge(int[] arr, int left, int mid, int right) {
        int[] tmp = new int[right - left + 1];
        int i = left, j = mid + 1, k = 0;
        while (i <= mid && j <= right) {
            if (arr[i] <= arr[j]) tmp[k++] = arr[i++];
            else tmp[k++] = arr[j++];
        }
        while (i <= mid) tmp[k++] = arr[i++];
        while (j <= right) tmp[k++] = arr[j++];
        System.arraycopy(tmp, 0, arr, left, tmp.length);
    }

    static void quickSort(int[] arr, int low, int high) {
        if (low < high) {
            int p = partition(arr, low, high);
            quickSort(arr, low, p - 1);
            quickSort(arr, p + 1, high);
        }
    }

    static int partition(int[] arr, int low, int high) {
        int pivot = arr[high];
        int i = low - 1;
        for (int j = low; j < high; j++) {
            if (arr[j] <= pivot) {
                i++;
                int tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
            }
        }
        int tmp = arr[i + 1]; arr[i + 1] = arr[high]; arr[high] = tmp;
        return i + 1;
    }

    static int binarySearch(int[] arr, int target) {
        int lo = 0, hi = arr.length - 1;
        while (lo <= hi) {
            int mid = (lo + hi) / 2;
            if (arr[mid] == target) return mid;
            else if (arr[mid] < target) lo = mid + 1;
            else hi = mid - 1;
        }
        return -1;
    }

    static int[] countingSort(int[] a, int max) {
        int[] count = new int[max + 1];
        for (int x : a) count[x]++;
        int[] out = new int[a.length];
        int idx = 0;
        for (int v = 0; v <= max; v++)
            for (int c = count[v]; c > 0; c--)
                out[idx++] = v;
        return out;
    }

    public static void main(String[] args) {
        int[] data = {5, 2, 9, 1, 5, 6, -3, 0};
        int[] a = data.clone();
        bubbleSort(a);
        System.out.println("Bubble: " + Arrays.toString(a));
        int[] b = Arrays.copyOf(data, data.length);
        insertionSort(b);
        System.out.println("Insertion: " + Arrays.toString(b));
        int[] c = data.clone();
        selectionSort(c);
        System.out.println("Selection: " + Arrays.toString(c));
        int[] d = data.clone();
        mergeSort(d, 0, d.length - 1);
        System.out.println("Merge: " + Arrays.toString(d));
        int[] e = data.clone();
        quickSort(e, 0, e.length - 1);
        System.out.println("Quick: " + Arrays.toString(e));
        System.out.println(binarySearch(e, 6) + " " + binarySearch(e, 7));
        System.out.println(Arrays.toString(countingSort(new int[]{3, 1, 2, 3, 0, 1}, 3)));
        int[] f = {4, 3, 2, 1};
        Arrays.sort(f);
        System.out.println(Arrays.toString(f) + " " + Arrays.equals(e, d));
        int[][] grid = new int[3][4];
        for (int i = 0; i < 3; i++)
            for (int j = 0; j < 4; j++)
                grid[i][j] = i * j;
        System.out.println(Arrays.toString(grid[2]) + " " + grid.length + " " + grid[0].length);
        int sum = 0;
        for (int[] row : grid) for (int v : row) sum += v;
        System.out.println("sum=" + sum + ", avg=" + (double) sum / 12 + ", half=" + sum / 5 + ", mod=" + sum % 5);
    }
}
