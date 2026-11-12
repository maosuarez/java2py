import java.util.*;

interface Shape {
    double area();
    default String describe() { return getName() + " with area " + String.format("%.2f", area()); }
    String getName();
}

abstract class Base implements Shape {
    protected static int created = 0;
    protected final String name;

    Base(String name) {
        this.name = name;
        created++;
    }

    public String getName() { return name; }

    public abstract double perimeter();

    @Override
    public String toString() { return name + "(" + String.format("%.1f", perimeter()) + ")"; }
}

class Circle extends Base {
    private final double r;
    static final double PI = 3.14159;

    Circle(double r) {
        super("Circle");
        this.r = r;
    }

    public double area() { return PI * r * r; }
    public double perimeter() { return 2 * PI * r; }
}

class Rect extends Base implements Comparable<Rect> {
    private double w, h;

    Rect(double w, double h) {
        super("Rect");
        this.w = w;
        this.h = h;
    }

    Rect(double side) {
        this(side, side);
    }

    public double area() { return w * h; }
    public double perimeter() { return 2 * (w + h); }

    @Override
    public int compareTo(Rect other) {
        return Double.compare(area(), other.area());
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Rect r = (Rect) o;
        return w == r.w && h == r.h;
    }

    @Override
    public int hashCode() { return Objects.hash(w, h); }
}

enum Level {
    LOW(1), MEDIUM(5), HIGH(10);

    private final int weight;

    Level(int weight) { this.weight = weight; }

    int getWeight() { return weight; }
}

enum Color { RED, GREEN, BLUE }

class InsufficientFundsException extends RuntimeException {
    InsufficientFundsException(String message) { super(message); }
}

class Account {
    private double balance;
    private final List<String> log = new ArrayList<>();

    void deposit(double amount) {
        if (amount <= 0) throw new IllegalArgumentException("Invalid amount");
        balance += amount;
        log.add("D" + amount);
    }

    void withdraw(double amount) {
        if (amount > balance) throw new InsufficientFundsException("Need " + (amount - balance) + " more");
        balance -= amount;
        log.add("W" + amount);
    }

    double getBalance() { return balance; }
    int entries() { return log.size(); }
}

public class Shapes {
    static String colorName(Color c) {
        switch (c) {
            case RED: return "rojo";
            case GREEN: return "verde";
            default: return "otro";
        }
    }

    static int sum(int... nums) {
        int total = 0;
        for (int n : nums) total += n;
        return total;
    }

    public static void main(String[] args) {
        List<Shape> shapes = new ArrayList<>();
        shapes.add(new Circle(1.5));
        shapes.add(new Rect(2, 3));
        shapes.add(new Rect(4));
        for (Shape s : shapes) System.out.println(s.describe() + " / " + s);
        System.out.println("created=" + Base.created);

        List<Rect> rects = new ArrayList<>();
        rects.add(new Rect(5, 5)); rects.add(new Rect(1, 2)); rects.add(new Rect(3));
        Collections.sort(rects);
        for (Rect r : rects) System.out.print(r.area() + " ");
        System.out.println();
        System.out.println(new Rect(2, 2).equals(new Rect(2)) + " " + (rects.get(0) == rects.get(0)) + " " + (new Rect(1).hashCode() == new Rect(1).hashCode()) + " " + (shapes.get(0) instanceof Circle));

        Level lv = Level.MEDIUM;
        System.out.println(lv + " " + lv.getWeight() + " " + (lv == Level.MEDIUM) + " " + Level.values().length + " " + colorName(Color.GREEN) + colorName(Color.BLUE) + " " + Color.valueOf("RED"));

        Account acc = new Account();
        acc.deposit(100);
        try {
            acc.withdraw(30);
            acc.withdraw(500);
        } catch (InsufficientFundsException e) {
            System.out.println("Caught: " + e.getMessage());
        } finally {
            System.out.println("balance=" + acc.getBalance() + " entries=" + acc.entries());
        }
        try {
            acc.deposit(-1);
        } catch (IllegalArgumentException | NullPointerException e) {
            System.out.println(e.getMessage());
        }
        try {
            int[] arr = new int[2];
            arr[5] = 1;
        } catch (ArrayIndexOutOfBoundsException e) {
            System.out.println("out of bounds");
        }
        System.out.println(sum() + " " + sum(1, 2, 3));
    }
}
