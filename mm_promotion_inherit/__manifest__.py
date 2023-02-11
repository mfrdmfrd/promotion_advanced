# -*- coding: utf-8 -*-
{
    'name': "mm_promotion_inherit",
    'author': "Mohamed Mamdouh",
    'website': "mamdouhabdelsameea@gmail.com",
    'category': 'Uncategorized',
    'version': '0.1',
    'depends': ['base', 'sale_coupon', 'coupon', 'sale', 'point_of_sale', 'sale_management'],
    "images": [
        'static/description/icon.png'
    ],
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'wizard/get_data.xml',
        'wizard/promotion_wizard.xml',
        'views/promotion_inherit.xml',

    ],

}
