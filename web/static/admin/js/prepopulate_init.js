'use strict';
{
    const $ = django.jQuery;
    const fields = $('#django-admin-prepopulated-fields-constants').data('prepopulatedFields');
    $.each(fields, function(index, field) {
<<<<<<< HEAD
        $('.empty-form .form-row .field-' + field.name + ', .empty-form.form-row .field-' + field.name).addClass('prepopulated_field');
=======
        $(
            '.empty-form .form-row .field-' + field.name +
            ', .empty-form.form-row .field-' + field.name +
            ', .empty-form .form-row.field-' + field.name
        ).addClass('prepopulated_field');
>>>>>>> 7ac3d760cfa05083e5d1c3ec4c1277d993f18c89
        $(field.id).data('dependency_list', field.dependency_list).prepopulate(
            field.dependency_ids, field.maxLength, field.allowUnicode
        );
    });
}
