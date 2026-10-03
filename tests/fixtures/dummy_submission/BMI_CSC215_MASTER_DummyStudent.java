import java.util.Scanner;

public class BMI_CSC215_MASTER_DummyStudent {
    public static void main(String[] args) {
        Scanner scanner = new Scanner(System.in);
        String mode = scanner.nextLine().trim();
        if (mode.equalsIgnoreCase("English")) {
            BMI_CSC215_English_DummyStudent.run(scanner);
            return;
        }
        if (mode.equalsIgnoreCase("Metric")) {
            BMI_CSC215_Metric_DummyStudent.run(scanner);
            return;
        }
        System.out.println("UNKNOWN_MODE");
    }
}
