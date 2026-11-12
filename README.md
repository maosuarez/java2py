# java2py

Traductor de **Java a Python** pensado para estudiar: tomas el código de un libro de
estructuras de datos y algoritmos escrito en Java y obtienes el mismo programa en Python,
legible y con las construcciones que usaría alguien que programa en Python.

- **Sin IA.** Analiza el Java con un parser real ([tree-sitter](https://tree-sitter.github.io/))
  y aplica reglas fijas: la misma entrada siempre produce la misma salida.
- **Acepta lo que le pegues:** un archivo completo, una clase, uno o varios métodos,
  sentencias sueltas o una sola expresión.
- **No inventa.** Lo que no sabe traducir queda como comentario `# TODO(java2py): ...` con el
  Java original, y además se informa como aviso.

## Instalación

```bash
pip install java2py
```

Requiere Python 3.10 o superior.

## Uso desde la terminal

```bash
java2py Pila.java                  # muestra el Python en pantalla
java2py Pila.java -o pila.py       # lo guarda en un archivo
java2py capitulo3/ -o capitulo3_py/  # traduce todos los .java de una carpeta
java2py -c "int mid = (lo + hi) / 2;"   # un fragmento
cat Pila.java | java2py -          # desde la entrada estándar
java2py -i                         # modo interactivo
```

Opciones: `--no-type-hints`, `--no-fstrings`, `--no-main`, `-q` (sin avisos).
También funciona como `python -m java2py`.

## Uso desde Python

```python
from java2py import translate, translate_detailed, translate_file

print(translate("int doble(int x) { return x * 2; }"))
# def doble(x: int) -> int:
#     return x * 2

resultado = translate_detailed(codigo_java)
print(resultado.code)        # el Python generado
print(resultado.warnings)    # lo que conviene revisar a mano

translate_file("Pila.java", "pila.py")
```

## Ejemplo

```java
public class Busqueda {
    static int binaria(int[] arr, int objetivo) {
        int lo = 0, hi = arr.length - 1;
        while (lo <= hi) {
            int mid = (lo + hi) / 2;
            if (arr[mid] == objetivo) return mid;
            else if (arr[mid] < objetivo) lo = mid + 1;
            else hi = mid - 1;
        }
        return -1;
    }

    public static void main(String[] args) {
        int[] datos = {1, 3, 5, 7, 9};
        System.out.println("Posición: " + binaria(datos, 7));
    }
}
```

```python
import sys


class Busqueda:
    @staticmethod
    def binaria(arr: list[int], objetivo: int) -> int:
        lo = 0
        hi = len(arr) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            if arr[mid] == objetivo:
                return mid
            elif arr[mid] < objetivo:
                lo = mid + 1
            else:
                hi = mid - 1
        return -1

    @staticmethod
    def main(args: list[str]) -> None:
        datos = [1, 3, 5, 7, 9]
        print(f"Posición: {Busqueda.binaria(datos, 7)}")


if __name__ == "__main__":
    Busqueda.main(sys.argv[1:])
```

## Qué traduce

| Java | Python |
| --- | --- |
| Clases, herencia, `super`, clases abstractas e interfaces | `class`, `ABC` y `@abstractmethod` |
| Campos y constructores | `__init__` con `self.campo = ...` |
| `static` (métodos y campos) | `@staticmethod` y atributos de clase |
| Sobrecarga de métodos y constructores | una función que elige la versión según los argumentos |
| `toString`, `equals`, `hashCode`, `compareTo` | `__str__`, `__eq__`, `__hash__`, `compareTo` + `__lt__` |
| `enum`, `record` | `Enum`, `@dataclass(frozen=True)` |
| Clases anidadas e internas | clases al nivel del módulo (las internas reciben la instancia externa) |
| `Iterable` / `Iterator` propios | `__iter__` / `__next__` para poder usar `for` |
| `for` con contador, `for-each`, `while`, `do-while` | `for ... in range(...)`, `for ... in`, `while` |
| `switch` (clásico y con `->`) | `match` / `case` |
| `try` / `catch` / `finally`, `throw`, try-with-resources | `try` / `except` / `finally`, `raise`, `with` |
| Arreglos (`new int[n]`, `new int[n][m]`, `{1, 2}`) | listas |
| `ArrayList`, `LinkedList`, `Stack` | `list` |
| `Queue`, `Deque`, `ArrayDeque` | `collections.deque` |
| `PriorityQueue` | lista + `heapq` |
| `HashMap`, `HashSet` (y variantes) | `dict`, `set` |
| `String`, `char`, `StringBuilder` | `str` (con `ord()`/`chr()` donde hace falta) |
| `"a" + x + "b"` | f-strings |
| `System.out.println/print/printf`, `String.format` | `print`, operador `%` |
| `Math`, `Integer`, `Character`, `Arrays`, `Collections`, `Objects`, `BigInteger` | `math`, funciones integradas, métodos de `list`/`str` |
| Lambdas y referencias a métodos | `lambda`, funciones |
| Excepciones de Java | la excepción de Python más cercana (`IllegalArgumentException` → `ValueError`...) |
| Javadoc y comentarios | docstrings y comentarios `#` |

Los nombres se conservan tal cual (`getNombre`, `insertarAlFinal`) para que puedas seguir el
libro línea por línea. Solo cambian cuando chocan con Python: `in` → `in_`, una variable
`max` → `max_`, y un campo que se llama igual que un método (`size` y `size()`) → `_size`.

## Diferencias entre Java y Python que debes conocer

La traducción busca el Python más cercano, pero los lenguajes no se comportan igual en todo:

- **División y módulo con negativos.** `-7 / 2` es `-3` en Java y `-7 // 2` es `-4` en Python
  (y `-7 % 2` da `-1` contra `1`). Con números no negativos el resultado es idéntico.
- **Enteros sin límite.** En Python no hay desbordamiento de `int`/`long`. Código que depende
  de él (algunas funciones hash, `>>>`) da resultados distintos.
- **Texto que se imprime.** `true`/`false`/`null` se imprimen como `True`/`False`/`None`, y un
  `HashMap` como `{'a': 1}` en vez de `{a=1}`.
- **`StringBuilder` se traduce como `str`**, que es inmutable. Si un método recibe un
  `StringBuilder` y lo modifica, quien lo llamó no verá el cambio.
- **Colas vacías y claves ausentes.** `queue.poll()` o `stack.peek()` sobre una estructura
  vacía devuelven `null` en Java; en Python lanzan `IndexError`. `map.get(k)` sí devuelve `None`.
- **`null`.** Llamar un método sobre `None` lanza `AttributeError`, no `NullPointerException`.
- **`Scanner`.** `nextInt()` se traduce como `int(input())`, que lee una línea completa.
- **`TreeMap` / `TreeSet`** se traducen como `dict` / `set`, que no mantienen orden por clave.
- **`PriorityQueue` con comparador.** `heapq` siempre es un min-heap; se deja un `TODO`.

## Lo que no traduce

Queda como `# TODO(java2py)` con el código original: streams (`.stream()`, `.forEach`),
clases anónimas, `break`/`continue` con etiqueta, hilos y concurrencia, reflexión y
bibliotecas externas. Los `import` de Java se descartan.

Si un archivo define dos clases anidadas con el mismo nombre (dos `Node` distintos), en Python
quedan al mismo nivel y chocan; se avisa cuando ocurre.

## Desarrollo

```bash
git clone https://github.com/maosuarez/java2py && cd java2py
pip install -e ".[dev]"
pytest
```

`tests/cases/` contiene programas Java completos junto con la salida real que producen en
Java (`.expected`); las pruebas los traducen, ejecutan el Python y comparan ambas salidas.

## Publicar en PyPI

La publicación es automática con *Trusted Publishing*: al crear un Release en GitHub, el
flujo `.github/workflows/publish.yml` corre las pruebas, construye el paquete y lo sube a PyPI.

1. Cambia `__version__` en `src/java2py/__init__.py`.
2. Crea un Release en GitHub con esa versión (por ejemplo `v0.1.0`).

## Licencia

MIT.
