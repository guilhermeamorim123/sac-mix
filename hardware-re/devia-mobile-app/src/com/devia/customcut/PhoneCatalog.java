package com.devia.customcut;

import java.util.ArrayList;
import java.util.List;

/**
 * Placeholder catalog structure, mirroring DragX's real brand-then-model
 * browsing flow (res/layout/layout_activity_classify_brand.xml + _model.xml
 * in the DragX project). Brand names are generic public facts (Apple,
 * Samsung, etc.), not anything proprietary. Model dimensions are NOT
 * included here on purpose -- neither DragX nor the Devia app bundle a
 * local phone-model measurement database; that data lives only on
 * Skycut's backend, which this project has no access to. Fabricating
 * plausible-looking dimensions here would risk someone mistaking them for
 * real, calibrated measurements and wasting material on a bad cut.
 *
 * Selecting a model in ModelActivity navigates to CutActivity with the
 * size fields left EMPTY -- this catalog is a browsing/UI placeholder
 * until real measurements are supplied (see project memory).
 */
final class PhoneCatalog {

    static final class Brand {
        final String name;
        final List<String> models;

        Brand(String name, List<String> models) {
            this.name = name;
            this.models = models;
        }
    }

    static List<Brand> BRANDS = buildBrands();

    private static List<Brand> buildBrands() {
        List<Brand> brands = new ArrayList<>();
        brands.add(new Brand("Apple", placeholderModels("iPhone")));
        brands.add(new Brand("Samsung", placeholderModels("Galaxy")));
        brands.add(new Brand("Xiaomi", placeholderModels("Redmi")));
        brands.add(new Brand("Motorola", placeholderModels("Moto")));
        return brands;
    }

    private static List<String> placeholderModels(String prefix) {
        List<String> models = new ArrayList<>();
        models.add(prefix + " (modelo exemplo 1 -- sem medida cadastrada)");
        models.add(prefix + " (modelo exemplo 2 -- sem medida cadastrada)");
        return models;
    }

    private PhoneCatalog() {
    }
}
