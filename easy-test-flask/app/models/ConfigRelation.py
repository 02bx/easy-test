"""
@Time    : 2020/4/18 19:08
@Author  : 郭家兴
@Email   : 302802003@qq.com
@File    : ConfigRelation.py
@Desc    : 工程配置-关联
"""
from lin.exception import UnknownException
from lin.interface import InfoCrud as Base
from lin.db import db
from sqlalchemy import Column, Integer, Boolean

from app.models.case import Case


class ConfigRelation(Base):
    id = Column(Integer, primary_key=True, autoincrement=True, comment='配置id')
    project_id = Column(Integer, nullable=False, comment='工程id')
    order = Column(Integer, nullable=False, comment='执行顺序')
    is_run = Column(Boolean, nullable=False, default=True, comment='是否执行')
    case_id = Column(Integer, nullable=False, comment='用例id')

    def __init__(self, project_id, case_id, is_run=True, order=0):
        super().__init__()
        self.project_id = project_id
        self.case_id = case_id
        self.is_run = is_run
        self.order = order

    @classmethod
    def get_configs(cls, project_id):
        results = cls.query.join(Case, cls.case_id == Case.id).filter(
            cls.project_id == project_id,
            Case.delete_time == None
        ).with_entities(
            cls.id,
            cls.project_id,
            cls.order,
            cls.is_run,
            cls.case_id,
            Case.name,
            Case.info,
            Case.url,
            Case._method.label('method'),
            Case._submit.label('submit'),
            Case.header,
            Case.data,
            Case._deal.label('deal'),
            Case.condition,
            Case._type.label('type'),
            Case.expect_result.label('expect_result'),
            Case._assertion.label('assertion')
        ).order_by(cls.order).all()
        configs = [dict(zip(result.keys(), result)) for result in results]
        return configs

    @classmethod
    def relation_config(cls, project_id, configs):
        # 获取新config id 列表(不包含需要新增的配置)
        new_config_ids = [config[0] for config in configs if config[0]]
        # 获取原config id 列表
        config_ids = cls.query.filter_by(project_id=project_id).with_entities(cls.id).all()
        old_config_ids = [list(x)[0] for x in config_ids]
        # 需要删除的config id 列表
        delete_config_ids = list(set(old_config_ids).difference(set(new_config_ids)))
        # 需要新增的配置
        add_configs = [config for config in configs if config[0] is None]
        # 需要修改的配置（原配置 已经除去被删除 且不包括新增配置）
        update_configs = [config for config in configs if config[0]]

        try:
            # 删除config
            if delete_config_ids:
                for cid in delete_config_ids:
                    config = cls.query.filter_by(id=cid, project_id=project_id).first_or_404()
                    db.session.delete(config)
                db.session.flush()

            # 新增config
            if add_configs:
                for c in add_configs:
                    case_id = c[1]
                    is_run = c[2]
                    order = c[3]
                    config = cls(project_id, case_id, is_run, order)
                    db.session.add(config)
                db.session.flush()

            # 修改原用例（非新增） 是否执行 排序
            if update_configs:
                for c in update_configs:
                    config_id = c[0]
                    is_run = c[2]
                    order = c[3]
                    config = cls.query.filter_by(id=config_id).first_or_404()
                    config.is_run = is_run
                    config.order = order
                db.session.flush()

            db.session.commit()
        except Exception:
            db.session.rollback()
            raise UnknownException(msg='修改配置异常')
