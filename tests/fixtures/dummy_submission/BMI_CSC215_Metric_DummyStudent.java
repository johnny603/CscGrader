import java.util.Locale;
import java.util.Scanner;

public class BMI_CSC215_Metric_DummyStudent {
    public static void main(String[] args) {
        run(new Scanner(System.in));
    }

    public static void run(Scanner scanner) {
        scanner.useLocale(Locale.US);
        System.out.println("METRIC");
        double weightKg = scanner.nextDouble();
        double heightMeters = scanner.nextDouble();
        double bmi = weightKg / (heightMeters * heightMeters);
        System.out.printf("BMI_METRIC=%.2f%n", bmi);
    }
}
