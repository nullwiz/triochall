from api.service_layer import unit_of_work
from sqlalchemy.sql import text


async def catalog(
    uow: unit_of_work.SqlAlchemyUnitOfWork, page: int = 1, page_size: int = 10
):
    async with uow:
        results = await uow.session.execute(
            text(
                """
                SELECT 
                products.id, 
                products.name, 
                products.price, 
                products.description, 
                json_agg(json_build_object('id', variations.id, 'name', \
                        variations.name, 'price', variations.price)) FILTER (WHERE variations.is_deleted = 0) as variations
                FROM 
                    products 
                LEFT JOIN 
                    variations 
                ON 
                    products.id = variations.product_id AND variations.is_deleted = 0
                WHERE 
                    products.is_deleted = 0
                GROUP BY 
                    products.id
                LIMIT :page_size 
                OFFSET (:page - 1) * :page_size                
                """
            ),
            {"page_size": page_size, "page": page},
        )

    return results.mappings().all()
