package edu.ncsu.introclass;

import edu.ncsu.config.Properties;
import edu.ncsu.utils.Utils;

import java.util.ArrayList;
import java.util.List;

public class IntroClassUtils {

    public static String DATASET = "introclass";

    public static List<String> listGeneratedFiles() {
        List<String> generatedFiles = new ArrayList<>();
        for (String problem: Utils.listDir(Properties.INTROCLASS_JAVA_FOLDER)) {
            String problemDir = Utils.pathJoin(Properties.INTROCLASS_JAVA_FOLDER, problem);
            generatedFiles.addAll(Utils.listGeneratedFiles(problemDir));
        }
        return generatedFiles;
    }

}
