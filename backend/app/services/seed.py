from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import Activity, AdminUser, MediaAsset, RewardTier, ScoreItem
from app.services.security import hash_password


async def seed_demo_data(session: AsyncSession, settings: Settings) -> None:
    """Create one editable demo event and an administrator for local development."""
    if not settings.seed_demo_data:
        return

    activity = await session.scalar(select(Activity).where(Activity.slug == "flipbelt-40s-demo"))
    if activity is None:
        activity = Activity(
            slug="flipbelt-40s-demo",
            title="FLIPBELT 40秒能装挑战",
            description="扫码报名，挑战40秒，看看你能装多少！",
            status="active",
            challenge_duration_seconds=40,
            challenge_limit=1,
            draw_threshold=45,
            rules_text=(
                "40秒内完成装载；道具必须完全装入袋鼠裤；"
                "掉落道具不计分；工作人员现场核算道具数量。"
            ),
        )
        session.add(activity)
        await session.flush()

        session.add_all(
            [
                ScoreItem(
                    activity_id=activity.id,
                    code="hidden_bonus",
                    name="隐藏加码道具",
                    points=6,
                    max_quantity=None,
                    is_hidden_bonus=True,
                    appear_at_seconds_remaining=5,
                    display_order=10,
                ),
                ScoreItem(
                    activity_id=activity.id,
                    code="light_clothing",
                    name="轻薄衣物",
                    points=6,
                    max_quantity=2,
                    display_order=20,
                ),
                ScoreItem(
                    activity_id=activity.id,
                    code="trekking_pole",
                    name="登山杖",
                    points=6,
                    max_quantity=1,
                    is_required=True,
                    display_order=30,
                ),
                ScoreItem(
                    activity_id=activity.id,
                    code="water_bottle",
                    name="水壶",
                    points=5,
                    max_quantity=1,
                    is_required=True,
                    display_order=40,
                ),
                ScoreItem(
                    activity_id=activity.id,
                    code="earphones",
                    name="耳机",
                    points=3,
                    max_quantity=1,
                    is_required=True,
                    display_order=50,
                ),
                ScoreItem(
                    activity_id=activity.id,
                    code="phone_model",
                    name="手机模型",
                    points=3,
                    max_quantity=1,
                    is_required=True,
                    display_order=60,
                ),
                ScoreItem(
                    activity_id=activity.id,
                    code="energy_gel",
                    name="能量胶",
                    points=2,
                    max_quantity=20,
                    display_order=70,
                ),
                ScoreItem(
                    activity_id=activity.id,
                    code="salt_pills",
                    name="盐丸类道具",
                    points=1,
                    max_quantity=20,
                    display_order=80,
                ),
            ]
        )
        session.add_all(
            [
                RewardTier(
                    activity_id=activity.id,
                    min_score=45,
                    max_score=None,
                    title="能装王者",
                    prize_name="运动短袜",
                    display_order=10,
                ),
                RewardTier(
                    activity_id=activity.id,
                    min_score=35,
                    max_score=44,
                    title="能装高手",
                    prize_name="小袋鼠钥匙扣",
                    display_order=20,
                ),
                RewardTier(
                    activity_id=activity.id,
                    min_score=25,
                    max_score=34,
                    title="能装达人",
                    prize_name="飞比特限定编织袋",
                    display_order=30,
                ),
                RewardTier(
                    activity_id=activity.id,
                    min_score=0,
                    max_score=24,
                    title="能装新手",
                    prize_name="冷感冰巾",
                    display_order=40,
                ),
            ]
        )
        session.add_all(
            [
                MediaAsset(
                    activity_id=activity.id,
                    kind="douyin_qr",
                    label="抖音二维码",
                    public_url="/assets/抖音二维码测试版.png",
                    mime_type="image/png",
                ),
                MediaAsset(
                    activity_id=activity.id,
                    kind="xiaohongshu_qr",
                    label="小红书二维码",
                    public_url="/assets/小红书二维码测试版.png",
                    mime_type="image/png",
                ),
                MediaAsset(
                    activity_id=activity.id,
                    kind="group_qr",
                    label="测试微信群二维码",
                    public_url="/assets/测试群二维码.jpg",
                    mime_type="image/jpeg",
                ),
                MediaAsset(
                    activity_id=activity.id,
                    kind="demo_video",
                    label="袋鼠裤示范视频",
                    public_url="/assets/袋鼠裤.mp4",
                    mime_type="video/mp4",
                ),
            ]
        )

    admin = await session.scalar(select(AdminUser).where(AdminUser.username == settings.demo_admin_username))
    if admin is None:
        session.add(
            AdminUser(
                username=settings.demo_admin_username,
                display_name="活动管理员",
                password_hash=hash_password(settings.demo_admin_password),
                role="admin",
            )
        )

    await session.commit()
