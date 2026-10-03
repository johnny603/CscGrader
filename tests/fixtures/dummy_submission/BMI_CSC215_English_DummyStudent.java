import java.util.Locale;
import java.util.Scanner;

public class BMI_CSC215_English_DummyStudent {
    public static void main(String[] args) {
        run(new Scanner(System.in));
    }

    public static void run(Scanner scanner) {
        scanner.useLocale(Locale.US);
        System.out.println("ENGLISH");
        double weightPounds = scanner.nextDouble();
        double heightInches = scanner.nextDouble();
        double bmi = (weightPounds * 703.0) / (heightInches * heightInches);
        System.out.printf("BMI_ENGLISH=%.2f%n", bmi);
    }
}
