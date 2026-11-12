import java.util.*;

public class Dijkstra {
    static class Arista {
        final int destino;
        final int peso;

        Arista(int destino, int peso) {
            this.destino = destino;
            this.peso = peso;
        }
    }

    static class Estado implements Comparable<Estado> {
        final int nodo;
        final int distancia;

        Estado(int nodo, int distancia) {
            this.nodo = nodo;
            this.distancia = distancia;
        }

        @Override
        public int compareTo(Estado o) {
            return Integer.compare(distancia, o.distancia);
        }
    }

    // Distancias mínimas desde origen; pesos no negativos.
    static int[] distancias(List<List<Arista>> grafo, int origen) {
        int n = grafo.size();
        int[] dist = new int[n];
        Arrays.fill(dist, Integer.MAX_VALUE);
        dist[origen] = 0;
        PriorityQueue<Estado> pq = new PriorityQueue<>();
        pq.add(new Estado(origen, 0));
        while (!pq.isEmpty()) {
            Estado actual = pq.poll();
            if (actual.distancia > dist[actual.nodo]) {
                continue;
            }
            for (Arista a : grafo.get(actual.nodo)) {
                int nueva = dist[actual.nodo] + a.peso;
                if (nueva < dist[a.destino]) {
                    dist[a.destino] = nueva;
                    pq.add(new Estado(a.destino, nueva));
                }
            }
        }
        return dist;
    }

    static void agregar(List<List<Arista>> g, int u, int v, int w) {
        g.get(u).add(new Arista(v, w));
        g.get(v).add(new Arista(u, w));
    }

    public static void main(String[] args) {
        int n = 6;
        List<List<Arista>> g = new ArrayList<>();
        for (int i = 0; i < n; i++) {
            g.add(new ArrayList<>());
        }
        agregar(g, 0, 1, 7);
        agregar(g, 0, 2, 9);
        agregar(g, 0, 5, 14);
        agregar(g, 1, 2, 10);
        agregar(g, 1, 3, 15);
        agregar(g, 2, 3, 11);
        agregar(g, 2, 5, 2);
        agregar(g, 3, 4, 6);
        agregar(g, 4, 5, 9);
        int[] d = distancias(g, 0);
        for (int i = 0; i < n; i++) {
            System.out.println("0 -> " + i + ": " + d[i]);
        }
    }
}
