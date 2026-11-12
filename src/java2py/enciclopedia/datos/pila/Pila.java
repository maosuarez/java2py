public class Pila {
    private int[] datos;
    private int tam;

    Pila() {
        datos = new int[2];
        tam = 0;
    }

    void apilar(int x) {
        if (tam == datos.length) {
            int[] nuevo = new int[datos.length * 2];
            for (int i = 0; i < tam; i++) {
                nuevo[i] = datos[i];
            }
            datos = nuevo;
        }
        datos[tam] = x;
        tam++;
    }

    int desapilar() {
        if (estaVacia()) {
            throw new RuntimeException("pila vacia");
        }
        tam--;
        return datos[tam];
    }

    int cima() {
        if (estaVacia()) {
            throw new RuntimeException("pila vacia");
        }
        return datos[tam - 1];
    }

    boolean estaVacia() {
        return tam == 0;
    }

    int tamano() {
        return tam;
    }

    public static void main(String[] args) {
        Pila p = new Pila();
        for (int i = 1; i <= 5; i++) {
            p.apilar(i * 10);
        }
        System.out.println("tamano: " + p.tamano());
        System.out.println("cima: " + p.cima());
        while (!p.estaVacia()) {
            System.out.println("desapilo " + p.desapilar());
        }
    }
}
